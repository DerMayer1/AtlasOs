from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.repositories.workspaces import (
    confirm_tracked_companies,
    create_workspace,
    delete_workspace,
    get_workspace,
    get_workspace_with_companies,
    list_workspaces,
    update_workspace,
    update_workspace_status,
)
from app.middleware.auth import require_auth
from app.middleware.rate_limit import limiter
from app.queue.client import enqueue_workspace_discovery
from app.schemas import (
    ConfirmTrackedCompaniesRequest,
    CreateWorkspaceRequest,
    UpdateWorkspaceRequest,
)

router = APIRouter(tags=["workspaces"])


def not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "WORKSPACE_NOT_FOUND", "message": "Workspace not found."},
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workspace_endpoint(
    body: CreateWorkspaceRequest,
    user: dict = Depends(require_auth),
) -> dict:
    workspace = await create_workspace(user["sub"], body.model_dump())
    return await get_workspace_with_companies(workspace["id"], user["sub"])


@router.get("")
async def list_workspaces_endpoint(
    user: dict = Depends(require_auth),
) -> dict:
    return {"items": await list_workspaces(user["sub"])}


@router.get("/{workspace_id}")
async def get_workspace_endpoint(
    workspace_id: str,
    user: dict = Depends(require_auth),
) -> dict:
    workspace = await get_workspace_with_companies(workspace_id, user["sub"])
    if not workspace:
        raise not_found()
    return workspace


@router.patch("/{workspace_id}")
async def update_workspace_endpoint(
    workspace_id: str,
    body: UpdateWorkspaceRequest,
    user: dict = Depends(require_auth),
) -> dict:
    payload = body.model_dump(exclude_none=True)
    workspace = await update_workspace(workspace_id, user["sub"], payload)
    if not workspace:
        raise not_found()
    return await get_workspace_with_companies(workspace_id, user["sub"])


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace_endpoint(
    workspace_id: str,
    user: dict = Depends(require_auth),
) -> None:
    if not await delete_workspace(workspace_id, user["sub"]):
        raise not_found()


@router.post("/{workspace_id}/discover", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/hour")
async def discover_competitors_endpoint(
    request,
    workspace_id: str,
    user: dict = Depends(require_auth),
) -> dict:
    workspace = await get_workspace(workspace_id, user["sub"])
    if not workspace:
        raise not_found()
    if workspace["status"] == "discovering":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DISCOVERY_RUNNING",
                "message": "Competitor discovery is already running.",
            },
        )

    await update_workspace_status(workspace_id, "discovering")
    await enqueue_workspace_discovery(workspace_id)
    return {"id": workspace_id, "status": "discovering"}


@router.put("/{workspace_id}/companies")
async def confirm_companies_endpoint(
    workspace_id: str,
    body: ConfirmTrackedCompaniesRequest,
    user: dict = Depends(require_auth),
) -> dict:
    workspace = await get_workspace(workspace_id, user["sub"])
    if not workspace:
        raise not_found()
    if workspace["status"] not in ("review", "active"):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DISCOVERY_REQUIRED",
                "message": "Run competitor discovery before confirming companies.",
            },
        )

    await confirm_tracked_companies(workspace_id, body.company_ids)
    await update_workspace_status(workspace_id, "active")
    return await get_workspace_with_companies(workspace_id, user["sub"])
