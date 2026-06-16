"""Lightweight API hardening middleware.

These controls are intentionally dependency-free. They are not a replacement for
an edge WAF or a shared Redis limiter, but they give the API a sane defensive
baseline in local, single-instance and small deployment modes.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _identity(request: Request) -> str:
    token = request.headers.get("x-api-key", "")
    if token:
        return f"key:{token[-12:]}"
    return f"ip:{_client_ip(request)}"


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
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst = max(1, burst)
        self.refill_per_second = max(1, requests_per_minute) / 60
        self.excluded_paths = excluded_paths
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path.startswith(self.excluded_paths):
            return await call_next(request)

        now = time.monotonic()
        key = _identity(request)
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
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


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse({"detail": "request body too large"}, status_code=413)
        return await call_next(request)


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
