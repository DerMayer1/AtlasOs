from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_user_id(request: Request) -> str:
    """
    Key rate limits by authenticated user_id (JWT sub claim).
    Falls back to IP address for unauthenticated requests (e.g. /health).
    This prevents bypass via IP rotation or proxies.
    """
    user = getattr(request.state, "user", None)
    if user and user.get("sub"):
        return f"user:{user['sub']}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=get_user_id)
