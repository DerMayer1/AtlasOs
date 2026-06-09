"""
Pipeline Runner
Executes all stages sequentially, passing PipelineContext through each.
Accepts an optional event_callback for SSE progress publishing.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from app.pipeline.context import CompanyInput, PipelineContext
from app.pipeline.stages.stage1_extractor import WebsiteExtractorStage
from app.pipeline.stages.stage2_classifier import CategoryClassifierStage
from app.pipeline.stages.stage3_searcher import CompetitorSearcherStage
from app.pipeline.stages.stage4_competitor_classifier import CompetitorClassifierStage
from app.pipeline.stages.stage5_positioning import PositioningAnalyzerStage
from app.pipeline.stages.stage6_gaps import GapDetectorStage
from app.pipeline.stages.stage7_recommendations import RecommendationEngineStage
from app.pipeline.stages.stage8_memo import MemoComposerStage

logger = logging.getLogger(__name__)

EventCallback = Callable[[str, dict], Awaitable[None]]

STAGES = [
    WebsiteExtractorStage(),
    CategoryClassifierStage(),
    CompetitorSearcherStage(),
    CompetitorClassifierStage(),
    PositioningAnalyzerStage(),
    GapDetectorStage(),
    RecommendationEngineStage(),
    MemoComposerStage(),
]


async def run_pipeline(
    company_input: CompanyInput,
    on_event: EventCallback | None = None,
) -> PipelineContext:
    ctx = PipelineContext(input=company_input)
    logger.info(f"Pipeline starting for: {company_input.company_name}")

    for stage in STAGES:
        if on_event:
            await on_event("stage_start", {
                "stage": stage.stage_number,
                "name": stage.stage_name,
            })

        t0 = time.perf_counter()
        await stage.run(ctx)
        duration_ms = int((time.perf_counter() - t0) * 1000)

        if ctx.aborted:
            if on_event:
                error = ctx.errors[-1]["error"] if ctx.errors else "Critical stage failed"
                await on_event("stage_failed", {
                    "stage": stage.stage_number,
                    "name": stage.stage_name,
                    "duration_ms": duration_ms,
                    "error": error,
                })
            break

        if on_event:
            await on_event("stage_complete", {
                "stage": stage.stage_number,
                "name": stage.stage_name,
                "duration_ms": duration_ms,
            })

    logger.info(
        f"Pipeline complete for {company_input.company_name} — "
        f"{len(ctx.competitors)} competitors found, "
        f"{len(ctx.errors)} errors"
    )
    return ctx
