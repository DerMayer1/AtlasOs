from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.db.repositories.analyses import (
    create_analysis,
    delete_analysis,
    get_analysis,
    list_analyses,
)
from app.db.repositories.memos import get_memo_by_analysis
from app.middleware.auth import require_auth
from app.queue.client import enqueue_analysis
from app.schemas import CreateAnalysisRequest, ExportMemoRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analyses"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_analysis_endpoint(
    body: CreateAnalysisRequest,
    user: dict = Depends(require_auth),
) -> dict:
    user_id = user["sub"]
    input_data = body.model_dump()

    record = await create_analysis(user_id, input_data, body.analysis_depth)
    analysis_id = record["id"]

    await enqueue_analysis(analysis_id, input_data)

    return {
        "id": analysis_id,
        "status": "pending",
        "created_at": record["created_at"],
        "stream_url": f"/v1/analyses/{analysis_id}/stream",
    }


@router.get("")
async def list_analyses_endpoint(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    user: dict = Depends(require_auth),
) -> dict:
    items, total = await list_analyses(user["sub"], limit=limit, offset=offset, status=status)
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/{analysis_id}")
async def get_analysis_endpoint(
    analysis_id: str,
    user: dict = Depends(require_auth),
) -> dict:
    record = await get_analysis(analysis_id, user["sub"])
    if not record:
        raise HTTPException(status_code=404, detail={"code": "ANALYSIS_NOT_FOUND", "message": "Analysis not found."})
    return record


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_analysis_endpoint(
    analysis_id: str,
    user: dict = Depends(require_auth),
) -> None:
    deleted = await delete_analysis(analysis_id, user["sub"])
    if not deleted:
        raise HTTPException(status_code=404, detail={"code": "ANALYSIS_NOT_FOUND", "message": "Analysis not found."})


@router.get("/{analysis_id}/stream")
async def stream_analysis(
    analysis_id: str,
    user: dict = Depends(require_auth),
) -> StreamingResponse:
    import asyncio
    import json

    from app.queue.client import get_redis

    record = await get_analysis(analysis_id, user["sub"])
    if not record:
        raise HTTPException(status_code=404, detail={"code": "ANALYSIS_NOT_FOUND", "message": "Analysis not found."})

    async def event_generator():
        r = await get_redis()
        pubsub = r.pubsub()
        channel = f"analysis:{analysis_id}:events"
        await pubsub.subscribe(channel)

        # If already complete, send final event immediately
        if record["status"] == "complete":
            yield f"event: analysis_complete\ndata: {json.dumps({'analysis_id': analysis_id, 'status': 'complete'})}\n\n"
            return

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    payload = json.loads(message["data"])
                    yield f"event: {payload['event']}\ndata: {json.dumps(payload['data'])}\n\n"
                    if payload["event"] in ("analysis_complete", "analysis_failed"):
                        break
        finally:
            await pubsub.unsubscribe(channel)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{analysis_id}/memo")
async def get_memo(
    analysis_id: str,
    user: dict = Depends(require_auth),
) -> dict:
    record = await get_analysis(analysis_id, user["sub"])
    if not record:
        raise HTTPException(status_code=404, detail={"code": "ANALYSIS_NOT_FOUND", "message": "Analysis not found."})
    if record["status"] != "complete":
        raise HTTPException(status_code=400, detail={"code": "ANALYSIS_INCOMPLETE", "message": "Analysis must be complete."})

    memo = await get_memo_by_analysis(analysis_id)
    if not memo:
        raise HTTPException(status_code=404, detail={"code": "MEMO_NOT_FOUND", "message": "Memo not found."})
    return memo


@router.post("/{analysis_id}/memo/export")
async def export_memo(
    analysis_id: str,
    body: ExportMemoRequest,
    user: dict = Depends(require_auth),
) -> dict:
    record = await get_analysis(analysis_id, user["sub"])
    if not record:
        raise HTTPException(status_code=404, detail={"code": "ANALYSIS_NOT_FOUND", "message": "Analysis not found."})

    memo = await get_memo_by_analysis(analysis_id)
    if not memo:
        raise HTTPException(status_code=404, detail={"code": "MEMO_NOT_FOUND", "message": "Memo not found."})

    if body.format == "markdown":
        return {
            "export_id": memo["id"],
            "format": "markdown",
            "content": memo["content_md"],
        }

    # PDF generation
    from app.services.export import generate_pdf
    pdf_bytes = await generate_pdf(memo["content_md"])

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=market-memo-{analysis_id[:8]}.pdf"},
    )
