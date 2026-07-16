"""API-key auth with two scopes: read and run (PRD R3).

Tokens are random secrets shown once at creation; only sha256 hashes are
stored. Every authenticated request leaves a trace via the key id in logs
(PRD principle 4: human decisions are traceable too).
"""

from __future__ import annotations

import hashlib
import secrets
import uuid

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.orm import Session

from atlas.platform.db.models import ApiKeyRow, OrganizationRow

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

SCOPE_READ = "read"
SCOPE_RUN = "run"
API_KEY_COOKIE = "atlas_api_key"
DEFAULT_ORG_ID = "org_default"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ensure_organization(
    session: Session,
    org_id: str,
    *,
    name: str | None = None,
    slug: str | None = None,
) -> OrganizationRow:
    row = session.get(OrganizationRow, org_id)
    if row is None:
        row = OrganizationRow(
            id=org_id,
            name=name or org_id,
            slug=slug or org_id.removeprefix("org_").replace("_", "-"),
        )
        session.add(row)
        session.flush()
    return row


def create_api_key(
    session: Session,
    name: str,
    scopes: list[str],
    org_id: str = DEFAULT_ORG_ID,
) -> tuple[ApiKeyRow, str]:
    """Returns (row, plaintext token). The token is never stored or shown again."""
    token = f"atlas_{secrets.token_urlsafe(32)}"
    ensure_organization(
        session, org_id, name="Default organization" if org_id == DEFAULT_ORG_ID else None
    )
    row = ApiKeyRow(
        id=f"key_{uuid.uuid4().hex[:12]}",
        org_id=org_id,
        name=name,
        key_hash=hash_token(token),
        scopes=",".join(scopes),
    )
    session.add(row)
    session.commit()
    return row, token


def require_scope(scope: str):
    def dependency(
        request: Request,
        token: str | None = Security(api_key_header),
    ) -> ApiKeyRow:
        # Browser clients authenticate through an HttpOnly, SameSite cookie
        # issued only by the explicit local-demo bootstrap. API clients and the
        # deployment proxy continue to use X-API-Key.
        token = token or request.cookies.get(API_KEY_COOKIE)
        if not token:
            raise HTTPException(status_code=401, detail="missing X-API-Key header")
        session_factory = request.app.state.container.session_factory
        with session_factory() as session:
            row = session.execute(
                select(ApiKeyRow).where(ApiKeyRow.key_hash == hash_token(token))
            ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=401, detail="invalid API key")
        if scope not in row.scopes.split(","):
            raise HTTPException(status_code=403, detail=f"API key lacks {scope!r} scope")
        request.state.api_key = row
        return row

    return Depends(dependency)
