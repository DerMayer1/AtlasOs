"""
Pipeline Runner
Executes all stages sequentially, passing PipelineContext through each.
Stages 1-4 implemented. Stages 5-8 are stubs to be filled in Week 3.
"""
from __future__ import annotations

import logging

from app.pipeline.context import CompanyInput, PipelineContext
from app.pipeline.stages.stage1_extractor import WebsiteExtractorStage
from app.pipeline.stages.stage2_classifier import CategoryClassifierStage
from app.pipeline.stages.stage3_searcher import CompetitorSearcherStage
from app.pipeline.stages.stage4_competitor_classifier import CompetitorClassifierStage

logger = logging.getLogger(__name__)

STAGES = [
    WebsiteExtractorStage(),
    CategoryClassifierStage(),
    CompetitorSearcherStage(),
    CompetitorClassifierStage(),
    # Stages 5-8 will be added in Week 3
]


async def run_pipeline(company_input: CompanyInput) -> PipelineContext:
    ctx = PipelineContext(input=company_input)
    logger.info(f"Pipeline starting for: {company_input.company_name}")

    for stage in STAGES:
        await stage.run(ctx)
        # If a critical stage fails (1-4), we can still continue with degraded output
        # The stage itself logs the error and leaves partial state intact

    logger.info(
        f"Pipeline complete for {company_input.company_name} — "
        f"{len(ctx.competitors)} competitors found, "
        f"{len(ctx.errors)} errors"
    )
    return ctx
