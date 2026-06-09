from __future__ import annotations

import logging

from app.pipeline.context import CompanyInput, PipelineContext
from app.pipeline.stages.stage1_extractor import WebsiteExtractorStage
from app.pipeline.stages.stage2_classifier import CategoryClassifierStage
from app.pipeline.stages.stage3_searcher import CompetitorSearcherStage
from app.pipeline.stages.stage4_competitor_classifier import CompetitorClassifierStage

logger = logging.getLogger(__name__)

DISCOVERY_STAGES = [
    WebsiteExtractorStage(),
    CategoryClassifierStage(),
    CompetitorSearcherStage(),
    CompetitorClassifierStage(),
]


async def run_discovery(company_input: CompanyInput) -> PipelineContext:
    ctx = PipelineContext(input=company_input)
    logger.info(f"Workspace discovery starting for: {company_input.company_name}")

    for stage in DISCOVERY_STAGES:
        await stage.run(ctx)
        if ctx.aborted:
            break

    logger.info(
        f"Workspace discovery complete for {company_input.company_name}: "
        f"{len(ctx.competitors)} competitors, {len(ctx.errors)} errors"
    )
    return ctx
