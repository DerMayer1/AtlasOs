"""Lightweight API hardening middleware.

These controls are intentionally dependency-free. They are not a replacement for
an edge WAF or a shared Redis limiter, but they give the API a sane defensive
baseline in local, single-instance and small deployment modes.

Proxy trust: ``X-Forwarded-For`` is only honoured when ``trusted_proxy_count``
is set to the real number of reverse proxies in front of the API. When it is 0
(the default, i.e. direct exposure) the header is ignored, because a client can
otherwise spoof it to mint unlimited rate-limit identities and bypass the
limiter entirely.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def _client_ip(request: Request, trusted_proxy_count: int = 0) -> str:
    """Best-effort client IP for rate limiting.

    With ``trusted_proxy_count`` proxies in front, the client address is the
    entry that many hops from the *right* of ``X-Forwarded-For`` — each trusted
    proxy appends to the right, so anything further left is client-supplied and
    untrusted. With no trusted proxies the header is ignored outright.
    """
    if trusted_proxy_count > 0:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            parts = [part.strip() for part in forwarded_for.split(",") if part.strip()]
            # Only trust the header when it is at least as long as the proxy
            # chain that should have produced it. A shorter chain means the
            # trusted proxies were not actually in front, so the peer IP below
            # is the real source — never a client-supplied entry.
            if len(parts) >= trusted_proxy_count:
                return parts[-trusted_proxy_count]
    if request.client:
        return request.client.host
    return "unknown"


def _identity(request: Request, trusted_proxy_count: int = 0) -> str:
    token = request.headers.get("x-api-key", "")
    if token:
        return f"key:{token[-12:]}"
    return f"ip:{_client_ip(request, trusted_proxy_count)}"


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        requests_per_minute: int,
        burst: int,
        excluded_paths: tuple[str, ...] = (),
        trusted_proxy_count: int = 0,
        max_tracked_identities: int = 100_000,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst = max(1, burst)
        self.refill_per_second = max(1, requests_per_minute) / 60
        self.excluded_paths = excluded_paths
        self.trusted_proxy_count = max(0, trusted_proxy_count)
        self.max_tracked_identities = max(1, max_tracked_identities)
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def _evict_locked(self, now: float) -> None:
        """Bound memory before inserting a new identity.

        A bucket that has refilled back to full is indistinguishable from a
        fresh one, so idle identities can be dropped without giving anyone extra
        allowance. If that is not enough, the oldest-seen identities go next.
        Only runs at the cap, so the steady state pays nothing.
        """
        full = self.burst
        stale = [
            key
            for key, bucket in self._buckets.items()
            if min(full, bucket.tokens + (now - bucket.updated_at) * self.refill_per_second)
            >= full
        ]
        for key in stale:
            del self._buckets[key]
        if len(self._buckets) >= self.max_tracked_identities:
            for key in sorted(self._buckets, key=lambda k: self._buckets[k].updated_at)[
                : len(self._buckets) - self.max_tracked_identities + 1
            ]:
                del self._buckets[key]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path.startswith(self.excluded_paths):
            return await call_next(request)

        now = time.monotonic()
        key = _identity(request, self.trusted_proxy_count)
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                if len(self._buckets) >= self.max_tracked_identities:
                    self._evict_locked(now)
                bucket = _Bucket(tokens=float(self.burst), updated_at=now)
                self._buckets[key] = bucket

            elapsed = now - bucket.updated_at
            bucket.tokens = min(self.burst, bucket.tokens + elapsed * self.refill_per_second)
            bucket.updated_at = now

            if bucket.tokens < 1:
                retry_after = max(1, int((1 - bucket.tokens) / self.refill_per_second))
                return JSONResponse(
                    {"detail": "rate limit exceeded"},
                    status_code=429,
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                    },
                )

            bucket.tokens -= 1
            remaining = str(max(0, int(bucket.tokens)))

        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(self.requests_per_minute))
        response.headers.setdefault("X-RateLimit-Remaining", remaining)
        return response


class MaxBodySizeMiddleware:
    """Reject over-limit request bodies, declared or streamed.

    Pure ASGI on purpose: the previous BaseHTTPMiddleware version only read
    ``Content-Length``, so a chunked upload (``Transfer-Encoding: chunked``, no
    declared length) sailed past it. This reads the body up to the cap, rejects
    before the app runs if it overflows, and otherwise replays the buffered body
    downstream. At most ``max_bytes`` (plus one chunk) is ever held.
    """

    def __init__(self, app, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = Headers(scope=scope).get("content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_bytes:
                    await self._reject(scope, receive, send)
                    return
            except ValueError:
                pass  # malformed header: fall through to streamed enforcement

        chunks: list[bytes] = []
        received = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                await self._reject(scope, receive, send)
                return
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break

        body = b"".join(chunks)
        replayed = False

        async def replay():
            nonlocal replayed
            if replayed:
                return {"type": "http.disconnect"}
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay, send)

    async def _reject(self, scope, receive, send) -> None:
        response = JSONResponse({"detail": "request body too large"}, status_code=413)
        await response(scope, receive, send)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        return response
