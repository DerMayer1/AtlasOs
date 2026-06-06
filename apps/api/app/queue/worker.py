"""
Pipeline Worker
Pulls jobs from Redis queue and executes the full 8-stage pipeline.
Publishes SSE-compatible progress events back to Redis pub/sub channel.
Run: python -m app.queue.worker
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from app.config import settings
from app.db.repositories.analyses import update_analysis_status
from app.db.repositories.memos import create_memo
from app.logging_config import configure_logging
from app.pipeline.context import CompanyInput
from app.pipeline.guards import write_cache
from app.pipeline.runner import run_pipeline
from app.queue.client import PIPELINE_QUEUE, get_redis

# Maximum times a job can be retried before being dropped
MAX_RETRIES = 0  # No retries — fail fast, surface error to user immediately

configure_logging()
logger = logging.getLogger(__name__)


async def publish_event(analysis_id: str, event: str, data: dict) -> None:
    r = await get_redis()
    channel = f"analysis:{analysis_id}:events"
    await r.publish(channel, json.dumps({"event": event, "data": data}))


async def process_job(job: dict) -> None:
    analysis_id = job["analysis_id"]
    logger.info(f"[Worker] Processing analysis {analysis_id}")
    t0 = time.perf_counter()

    try:
        await update_analysis_status(analysis_id, "running")
        await publish_event(analysis_id, "pipeline_start", {"analysis_id": analysis_id})

        company_input = CompanyInput(
            company_name=job["company_name"],
            website_url=job["website_url"],
            description=job["description"],
            target_market=job.get("target_market"),
            known_competitors=job.get("known_competitors", []),
            analysis_depth=job.get("analysis_depth", "standard"),
        )

        async def on_event(event: str, data: dict) -> None:
            await publish_event(analysis_id, event, data)

        ctx = await run_pipeline(company_input, on_event=on_event)

        duration_ms = int((time.perf_counter() - t0) * 1000)

        # Abort: pipeline was short-circuited due to critical stage failure
        if ctx.aborted:
            error_msg = f"Pipeline aborted at stage {ctx.abort_stage}"
            logger.error(f"[Worker] {error_msg} for {analysis_id}")
            await update_analysis_status(analysis_id, "failed", error=error_msg)
            await publish_event(analysis_id, "analysis_failed", {"analysis_id": analysis_id, "error": error_msg})
            return

        if ctx.errors:
            await update_analysis_status(analysis_id, "failed", error=str(ctx.errors))
            await publish_event(analysis_id, "analysis_failed", {"analysis_id": analysis_id, "error": str(ctx.errors)})
            return

        # Serialize result
        result = {
            "category": {"label": ctx.category.label, "definition": ctx.category.definition} if ctx.category else None,
            "competitors": [
                {"name": c.name, "website": c.website, "type": c.type, "threat_level": c.threat_level, "summary": c.summary, "positioning": c.positioning}
                for c in ctx.competitors
            ],
            "positioning_map": {
                "x_axis": ctx.positioning_map.x_axis,
                "y_axis": ctx.positioning_map.y_axis,
                "entities": [{"name": e.name, "x": e.x, "y": e.y, "is_subject": e.is_subject} for e in ctx.positioning_map.entities],
            } if ctx.positioning_map else None,
            "gaps": [{"description": g.description, "addressability": g.addressability, "risk": g.risk} for g in ctx.gaps],
            "recommendations": [{"type": r.type, "description": r.description, "impact": r.impact, "risk": r.risk} for r in ctx.recommendations],
            "memo_markdown": ctx.memo_markdown,
        }

        await update_analysis_status(analysis_id, "complete", result=result, duration_ms=duration_ms)
        await create_memo(analysis_id, ctx.memo_markdown)

        # Cache successful result to prevent duplicate LLM calls for same URL
        await write_cache(job["website_url"], job.get("analysis_depth", "standard"), result)

        await publish_event(analysis_id, "analysis_complete", {"analysis_id": analysis_id, "status": "complete"})
        logger.info(f"[Worker] Analysis {analysis_id} complete in {duration_ms}ms")

    except Exception as e:
        logger.exception(f"[Worker] Unexpected error for {analysis_id}: {e}")
        await update_analysis_status(analysis_id, "failed", error=str(e))
        await publish_event(analysis_id, "analysis_failed", {"analysis_id": analysis_id, "error": str(e)})


async def run_worker() -> None:
    logger.info("[Worker] Starting — listening on queue: " + PIPELINE_QUEUE)
    r = await get_redis()
    while True:
        try:
            item = await r.blpop(PIPELINE_QUEUE, timeout=5)
            if item:
                _, raw = item
                job = json.loads(raw)
                asyncio.create_task(process_job(job))
        except Exception as e:
            logger.error(f"[Worker] Queue error: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run_worker())
