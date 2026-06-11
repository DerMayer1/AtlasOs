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

from postgrest.exceptions import APIError

from app.db.repositories.analyses import update_analysis_status
from app.db.repositories.memos import create_memo
from app.db.repositories.signals import upsert_signals
from app.db.repositories.workspaces import (
    company_change_exists,
    create_company_change,
    create_company_snapshot,
    create_workspace_report,
    get_latest_snapshot,
    get_workspace_internal,
    has_workspace_report,
    list_confirmed_companies,
    replace_discovered_companies,
    set_companies_monitoring_status,
    set_company_ats,
    set_company_ingestion_status,
    update_workspace_status,
)
from app.logging_config import configure_logging
from app.pipeline.ats import ATSHandle, resolve_ats
from app.pipeline.change_classifier import classify_change, fallback_classification
from app.pipeline.change_detection import compare_snapshot_text
from app.pipeline.context import CompanyInput
from app.pipeline.discovery import run_discovery
from app.pipeline.guards import write_cache
from app.pipeline.hiring import build_hiring_signals, fetch_jobs
from app.pipeline.runner import run_pipeline
from app.pipeline.snapshot import capture_website_snapshot
from app.queue.client import PIPELINE_QUEUE, get_redis
from app.services.workspace_reports import build_baseline_report, build_change_report

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
            await publish_event(
                analysis_id,
                "analysis_failed",
                {"analysis_id": analysis_id, "error": error_msg},
            )
            return

        if ctx.errors:
            await update_analysis_status(analysis_id, "failed", error=str(ctx.errors))
            await publish_event(
                analysis_id,
                "analysis_failed",
                {"analysis_id": analysis_id, "error": str(ctx.errors)},
            )
            return

        # Serialize result
        result = {
            "category": (
                {
                    "label": ctx.category.label,
                    "definition": ctx.category.definition,
                }
                if ctx.category
                else None
            ),
            "competitors": [
                {
                    "name": c.name,
                    "website": c.website,
                    "type": c.type,
                    "threat_level": c.threat_level,
                    "summary": c.summary,
                    "positioning": c.positioning,
                }
                for c in ctx.competitors
            ],
            "positioning_map": {
                "x_axis": ctx.positioning_map.x_axis,
                "y_axis": ctx.positioning_map.y_axis,
                "entities": [
                    {
                        "name": e.name,
                        "x": e.x,
                        "y": e.y,
                        "is_subject": e.is_subject,
                    }
                    for e in ctx.positioning_map.entities
                ],
            }
            if ctx.positioning_map
            else None,
            "gaps": [
                {
                    "description": g.description,
                    "addressability": g.addressability,
                    "risk": g.risk,
                }
                for g in ctx.gaps
            ],
            "recommendations": [
                {
                    "type": r.type,
                    "description": r.description,
                    "impact": r.impact,
                    "risk": r.risk,
                }
                for r in ctx.recommendations
            ],
            "memo_markdown": ctx.memo_markdown,
        }

        await update_analysis_status(
            analysis_id,
            "complete",
            result=result,
            duration_ms=duration_ms,
        )
        await create_memo(analysis_id, ctx.memo_markdown)

        # Cache successful result to prevent duplicate LLM calls for same URL
        await write_cache(job["website_url"], job.get("analysis_depth", "standard"), result)

        await publish_event(
            analysis_id,
            "analysis_complete",
            {"analysis_id": analysis_id, "status": "complete"},
        )
        logger.info(f"[Worker] Analysis {analysis_id} complete in {duration_ms}ms")

    except Exception as e:
        logger.exception(f"[Worker] Unexpected error for {analysis_id}: {e}")
        await update_analysis_status(analysis_id, "failed", error=str(e))
        await publish_event(
            analysis_id,
            "analysis_failed",
            {"analysis_id": analysis_id, "error": str(e)},
        )


async def process_workspace_discovery(job: dict) -> None:
    workspace_id = job["workspace_id"]
    logger.info(f"[Worker] Discovering competitors for workspace {workspace_id}")

    try:
        workspace = await get_workspace_internal(workspace_id)
        if not workspace:
            logger.warning(f"[Worker] Workspace {workspace_id} no longer exists")
            return

        company_input = CompanyInput(
            company_name=workspace["company_name"],
            website_url=workspace["website_url"],
            description=workspace["description"],
            target_market=workspace.get("target_market"),
            analysis_depth="quick",
        )
        ctx = await run_discovery(company_input)

        if ctx.aborted or ctx.errors:
            error = ctx.errors[-1]["error"] if ctx.errors else "Discovery failed"
            await update_workspace_status(workspace_id, "failed", error=error)
            return

        competitors = [
            {
                "name": competitor.name,
                "website": competitor.website,
                "type": competitor.type,
                "threat_level": competitor.threat_level,
                "summary": competitor.summary,
                "positioning": competitor.positioning,
            }
            for competitor in ctx.competitors
        ]
        await replace_discovered_companies(workspace_id, competitors)
        await update_workspace_status(
            workspace_id,
            "review",
            category_label=ctx.category.label if ctx.category else None,
            category_definition=ctx.category.definition if ctx.category else None,
        )
        logger.info(
            f"[Worker] Workspace {workspace_id} ready for review "
            f"with {len(competitors)} competitors"
        )
    except Exception as exc:
        logger.exception(f"[Worker] Workspace discovery failed for {workspace_id}: {exc}")
        await update_workspace_status(workspace_id, "failed", error=str(exc))


async def process_workspace_snapshot(job: dict) -> None:
    workspace_id = job["workspace_id"]
    logger.info(f"[Worker] Capturing baseline for workspace {workspace_id}")

    try:
        workspace = await get_workspace_internal(workspace_id)
        if not workspace:
            logger.warning(f"[Worker] Workspace {workspace_id} no longer exists")
            return
        companies = await list_confirmed_companies(workspace_id)
        semaphore = asyncio.Semaphore(4)
        detected_changes: list[dict] = []

        async def capture_company(company: dict) -> None:
            company_id = company["id"]
            website_url = company.get("website_url")
            if not website_url:
                await set_companies_monitoring_status(
                    workspace_id,
                    "failed",
                    company_id=company_id,
                    error="No website URL is available for this company.",
                )
                return

            async with semaphore:
                await set_companies_monitoring_status(
                    workspace_id,
                    "running",
                    company_id=company_id,
                )
                try:
                    previous = await get_latest_snapshot(company_id)
                    snapshot = await capture_website_snapshot(website_url)
                    current = await create_company_snapshot(
                        workspace_id,
                        company_id,
                        snapshot.to_record(),
                    )
                    if (
                        not previous
                        or previous["content_hash"] == current["content_hash"]
                        or await company_change_exists(previous["id"], current["id"])
                    ):
                        return

                    diff = compare_snapshot_text(
                        previous["content_text"],
                        current["content_text"],
                    )
                    if not diff.meaningful:
                        return

                    try:
                        classification = await classify_change(company["name"], diff)
                    except Exception as exc:
                        logger.warning(
                            "[Worker] Change classification failed for company %s: %s",
                            company_id,
                            exc,
                        )
                        classification = fallback_classification(company["name"])

                    try:
                        change = await create_company_change(
                            workspace_id,
                            company_id,
                            previous["id"],
                            current["id"],
                            classification.model_dump(),
                            {
                                "added": diff.added,
                                "removed": diff.removed,
                                "similarity": round(diff.similarity, 4),
                                "changed_characters": diff.changed_characters,
                            },
                        )
                    except APIError as exc:
                        # A concurrent snapshot run already recorded this change
                        # (violates the unique(previous, current) constraint).
                        if exc.code == "23505":
                            logger.info(
                                "[Worker] Change for company %s already recorded "
                                "by a concurrent run; skipping",
                                company_id,
                            )
                            return
                        raise
                    detected_changes.append(change)
                except Exception as exc:
                    logger.warning(
                        f"[Worker] Snapshot failed for company {company_id}: {exc}"
                    )
                    await set_companies_monitoring_status(
                        workspace_id,
                        "failed",
                        company_id=company_id,
                        error=str(exc),
                    )

        await asyncio.gather(*(capture_company(company) for company in companies))

        if detected_changes:
            title, content = build_change_report(
                workspace,
                detected_changes,
                {company["id"]: company for company in companies},
            )
            await create_workspace_report(
                workspace_id,
                "change",
                title,
                content,
                {"change_ids": [change["id"] for change in detected_changes]},
            )
        elif not await has_workspace_report(workspace_id, "baseline"):
            refreshed_companies = await list_confirmed_companies(workspace_id)
            title, content = build_baseline_report(workspace, refreshed_companies)
            await create_workspace_report(
                workspace_id,
                "baseline",
                title,
                content,
                {"company_count": len(refreshed_companies)},
            )

        logger.info(
            "[Worker] Snapshot capture complete for workspace %s with %s changes",
            workspace_id,
            len(detected_changes),
        )
    except Exception as exc:
        logger.exception(
            f"[Worker] Workspace baseline failed for {workspace_id}: {exc}"
        )
        await set_companies_monitoring_status(
            workspace_id,
            "failed",
            error=str(exc),
        )


async def process_workspace_ingestion(job: dict) -> None:
    workspace_id = job["workspace_id"]
    logger.info("[Worker] Running engine v2 ingestion for workspace %s", workspace_id)

    workspace = await get_workspace_internal(workspace_id)
    if not workspace:
        logger.warning("[Worker] Workspace %s no longer exists", workspace_id)
        return

    companies = await list_confirmed_companies(workspace_id)
    semaphore = asyncio.Semaphore(4)

    async def ingest_company(company: dict) -> None:
        company_id = company["id"]
        await set_company_ingestion_status(
            workspace_id,
            "running",
            company_id=company_id,
        )
        try:
            provider = company.get("ats_provider")
            slug = company.get("ats_slug")
            if provider and slug:
                handle = ATSHandle(provider=provider, slug=slug, source="stored")
            else:
                handle = await resolve_ats(company["name"], company.get("website_url"))
                if handle:
                    await set_company_ats(
                        company_id,
                        provider=handle.provider,
                        slug=handle.slug,
                    )

            if not handle:
                raise ValueError("No supported public ATS board was found.")

            jobs = await fetch_jobs(handle)
            signals = build_hiring_signals(
                workspace_id,
                company_id,
                jobs,
                provider=handle.provider,
                slug=handle.slug,
            )
            await upsert_signals(signals)
            await set_company_ingestion_status(
                workspace_id,
                "ready",
                company_id=company_id,
            )
            logger.info(
                "[Worker] Ingested %s hiring signals for %s (%s open roles)",
                len(signals),
                company["name"],
                len(jobs),
            )
        except Exception as exc:
            logger.warning(
                "[Worker] Engine v2 ingestion failed for company %s: %s",
                company_id,
                exc,
            )
            await set_company_ingestion_status(
                workspace_id,
                "failed",
                company_id=company_id,
                error=str(exc),
            )

    async def limited_ingest(company: dict) -> None:
        async with semaphore:
            await ingest_company(company)

    await asyncio.gather(*(limited_ingest(company) for company in companies))
    logger.info("[Worker] Engine v2 ingestion complete for workspace %s", workspace_id)


async def dispatch_job(job: dict) -> None:
    job_type = job.get("job_type", "analysis")
    if job_type == "analysis":
        await process_job(job)
        return
    if job_type == "workspace_discovery":
        await process_workspace_discovery(job)
        return
    if job_type == "workspace_snapshot":
        await process_workspace_snapshot(job)
        return
    if job_type == "workspace_ingestion":
        await process_workspace_ingestion(job)
        return
    logger.error(f"[Worker] Unknown job type: {job_type}")


_shutdown = False


async def run_worker() -> None:
    import signal

    def _handle_shutdown(sig, frame):
        global _shutdown
        logger.info(f"[Worker] Received signal {sig} — draining and shutting down...")
        _shutdown = True

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    logger.info("[Worker] Starting — listening on queue: " + PIPELINE_QUEUE)
    r = await get_redis()

    pending_tasks: set[asyncio.Task] = set()

    while not _shutdown:
        try:
            item = await r.blpop(PIPELINE_QUEUE, timeout=30)
            if item:
                _, raw = item
                job = json.loads(raw)
                task = asyncio.create_task(dispatch_job(job))
                pending_tasks.add(task)
                task.add_done_callback(pending_tasks.discard)
            # item is None when blpop times out with no jobs — this is normal
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Worker] Queue error: {e}")
            await asyncio.sleep(1)

    # Drain: wait for in-flight jobs to complete before exiting
    if pending_tasks:
        logger.info(f"[Worker] Draining {len(pending_tasks)} in-flight jobs...")
        await asyncio.gather(*pending_tasks, return_exceptions=True)

    logger.info("[Worker] Shutdown complete")


if __name__ == "__main__":
    asyncio.run(run_worker())
