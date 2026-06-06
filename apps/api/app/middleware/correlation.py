"""
Correlation ID Middleware
Attaches a unique X-Request-ID to every request and response.
Allows tracing a specific request across logs, SSE events, and worker jobs.
"""
from __future__ import annotations

import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Accept an incoming ID from the client (e.g. frontend or load balancer)
        # or generate a new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
