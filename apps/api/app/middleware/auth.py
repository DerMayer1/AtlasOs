from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.client import get_client

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    token = credentials.credentials
    try:
        client = await get_client()
        response = await client.auth.get_user(token)
        user = response.user if response else None
        if not user:
            raise ValueError("Supabase returned no user")

        payload = {
            "sub": str(user.id),
            "email": user.email,
        }

        # Attach to request.state so rate limiter can key by user_id
        request.state.user = payload
        return payload

    except Exception as e:
        logger.warning(f"[Auth] JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or expired token."},
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
