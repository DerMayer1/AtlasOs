from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.db.repositories.signals import list_signals
from app.db.repositories.workspaces import (
    confirm_tracked_companies,
    create_workspace,
    delete_workspace,
    get_workspace,
    get_workspace_report,
    get_workspace_with_companies,
    list_company_changes,
    list_snapshots,
    list_workspace_reports,
    list_workspaces,
    restore_companies_monitoring_status,
    set_companies_monitoring_status,
    set_company_ingestion_status,
    update_workspace,
    update_workspace_status,
)
from app.middleware.auth import require_auth
from app.middleware.rate_limit import limiter
from app.queue.client import (
    enqueue_workspace_discovery,
    enqueue_workspace_ingestion,
    enqueue_workspace_snapshot,
)
from app.schemas import (
    ConfirmTrackedCompaniesRequest,
    CreateWorkspaceRequest,
    ExportMemoRequest,
    UpdateWorkspaceRequest,
)

router = APIRouter(tags=["workspaces"])


def not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "WORKSPACE_NOT_FOUND", "message": "Workspace not found."},
    )


async def enqueue_snapshot_baseline(workspace_id: str) -> bool:
    await set_companies_monitoring_status(workspace_id, "pending")
    try:
        await enqueue_workspace_snapshot(workspace_id)
    except Exception:
        await restore_companies_monitoring_status(workspace_id)
        return False
    return True


async def start_workspace_ingestion(workspace_id: str) -> bool:
    await set_company_ingestion_status(workspace_id, "pending")
    try:
        await enqueue_workspace_ingestion(workspace_id)
    except Exception:
        await set_company_ingestion_status(
            workspace_id,
            "failed",
            error="Engine v2 ingestion could not be queued.",
        )
        return False
    return True


async def start_workspace_discovery(workspace_id: str) -> None:
    await update_workspace_status(workspace_id, "discovering")
    try:
        await enqueue_workspace_discovery(workspace_id)
    except Exception:
        await update_workspace_status(
            workspace_id,
            "failed",
            error="Competitor discovery could not be queued. Try again shortly.",
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DISCOVERY_QUEUE_UNAVAILABLE",
                "message": "Competitor discovery could not be started.",
            },
        ) from None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workspace_endpoint(
    body: CreateWorkspaceRequest,
    user: dict = Depends(require_auth),
) -> dict:
    workspace = await create_workspace(user["sub"], body.model_dump())
    await start_workspace_discovery(workspace["id"])
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

    await start_workspace_discovery(workspace_id)
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
    await start_workspace_ingestion(workspace_id)
    return await get_workspace_with_companies(workspace_id, user["sub"])


@router.post("/{workspace_id}/ingest", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("12/hour")
async def ingest_workspace_endpoint(
    request,
    workspace_id: str,
    user: dict = Depends(require_auth),
) -> dict:
    workspace = await get_workspace_with_companies(workspace_id, user["sub"])
    if not workspace:
        raise not_found()
    if workspace["status"] != "active":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "WORKSPACE_NOT_ACTIVE",
                "message": "Confirm the competitive set before running ingestion.",
            },
        )
    if any(
        company.get("ingestion_status") in ("pending", "running")
        for company in workspace["companies"]
        if company["is_confirmed"]
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INGESTION_RUNNING",
                "message": "Engine v2 ingestion is already running.",
            },
        )
    if not await start_workspace_ingestion(workspace_id):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "INGESTION_QUEUE_UNAVAILABLE",
                "message": "Engine v2 ingestion could not be started.",
            },
        )
    return {"id": workspace_id, "status": "pending"}


@router.get("/{workspace_id}/signals")
async def list_signals_endpoint(
    workspace_id: str,
    company_id: str | None = None,
    source: str | None = Query(default=None, pattern="^(hiring|pricing|reviews|releases|web)$"),
    metric: str | None = None,
    since: str | None = None,
    limit: int = Query(default=1000, ge=1, le=5000),
    user: dict = Depends(require_auth),
) -> dict:
    if not await get_workspace(workspace_id, user["sub"]):
        raise not_found()
    return {
        "items": await list_signals(
            workspace_id,
            company_id=company_id,
            source=source,
            metric=metric,
            since=since,
            limit=limit,
        )
    }


@router.post("/{workspace_id}/snapshots", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("12/hour")
async def capture_snapshots_endpoint(
    request,
    workspace_id: str,
    user: dict = Depends(require_auth),
) -> dict:
    workspace = await get_workspace_with_companies(workspace_id, user["sub"])
    if not workspace:
        raise not_found()
    if workspace["status"] != "active":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "WORKSPACE_NOT_ACTIVE",
                "message": "Confirm the competitive set before capturing snapshots.",
            },
        )
    if any(
        company["monitoring_status"] in ("pending", "running")
        for company in workspace["companies"]
        if company["is_confirmed"]
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "SNAPSHOT_RUNNING",
                "message": "A workspace snapshot is already running.",
            },
        )

    if not await enqueue_snapshot_baseline(workspace_id):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "SNAPSHOT_QUEUE_UNAVAILABLE",
                "message": "Monitoring could not be started. Try again shortly.",
            },
        )
    return {"id": workspace_id, "status": "pending"}


@router.get("/{workspace_id}/snapshots")
async def list_snapshots_endpoint(
    workspace_id: str,
    company_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(require_auth),
) -> dict:
    workspace = await get_workspace(workspace_id, user["sub"])
    if not workspace:
        raise not_found()
    return {
        "items": await list_snapshots(
            workspace_id,
            company_id=company_id,
            limit=limit,
        )
    }


@router.get("/{workspace_id}/changes")
async def list_changes_endpoint(
    workspace_id: str,
    company_id: str | None = None,
    relevance: str | None = Query(default=None, pattern="^(low|medium|high)$"),
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(require_auth),
) -> dict:
    if not await get_workspace(workspace_id, user["sub"]):
        raise not_found()
    return {
        "items": await list_company_changes(
            workspace_id,
            company_id=company_id,
            relevance=relevance,
            limit=limit,
        )
    }


@router.get("/{workspace_id}/reports")
async def list_reports_endpoint(
    workspace_id: str,
    user: dict = Depends(require_auth),
) -> dict:
    if not await get_workspace(workspace_id, user["sub"]):
        raise not_found()
    return {"items": await list_workspace_reports(workspace_id)}


@router.get("/{workspace_id}/reports/{report_id}")
async def get_report_endpoint(
    workspace_id: str,
    report_id: str,
    user: dict = Depends(require_auth),
) -> dict:
    if not await get_workspace(workspace_id, user["sub"]):
        raise not_found()
    report = await get_workspace_report(report_id, workspace_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPORT_NOT_FOUND", "message": "Report not found."},
        )
    return report


@router.post("/{workspace_id}/reports/{report_id}/export")
async def export_report_endpoint(
    workspace_id: str,
    report_id: str,
    body: ExportMemoRequest,
    user: dict = Depends(require_auth),
):
    if not await get_workspace(workspace_id, user["sub"]):
        raise not_found()
    report = await get_workspace_report(report_id, workspace_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPORT_NOT_FOUND", "message": "Report not found."},
        )
    if body.format == "markdown":
        return {
            "export_id": report["id"],
            "format": "markdown",
            "content": report["content_md"],
        }

    from app.services.export import generate_pdf

    pdf_bytes = await generate_pdf(report["content_md"])
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=atlasos-report-{report_id[:8]}.pdf"
            )
        },
    )
