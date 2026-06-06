"""
Smoke test — runs Stages 1-4 against a real company.
Requires OPENAI_API_KEY and TAVILY_API_KEY in .env
Run: pytest tests/test_pipeline_smoke.py -v -s
"""
import asyncio
import pytest
from app.pipeline.context import CompanyInput
from app.pipeline.runner import run_pipeline


@pytest.mark.asyncio
async def test_pipeline_stages_1_to_4():
    company = CompanyInput(
        company_name="Linear",
        website_url="https://linear.app",
        description="Linear is a project management tool built for modern software teams. It helps teams plan, track, and ship product work.",
        target_market="B2B SaaS, software engineering teams",
        known_competitors=["Jira", "Asana"],
        analysis_depth="standard",
    )

    ctx = await run_pipeline(company)

    # Stage 1
    assert ctx.raw_text, "Stage 1: raw_text should not be empty"
    print(f"\n[Stage 1] Extracted {len(ctx.raw_text)} chars")

    # Stage 2
    assert ctx.category is not None, "Stage 2: category should be set"
    assert ctx.category.label, "Stage 2: category label should not be empty"
    print(f"[Stage 2] Category: {ctx.category.label}")
    print(f"          Definition: {ctx.category.definition}")

    # Stage 3
    assert len(ctx.search_results) > 0, "Stage 3: should return search results"
    print(f"[Stage 3] Search results: {len(ctx.search_results)}")

    # Stage 4
    assert len(ctx.competitors) > 0, "Stage 4: should classify at least one competitor"
    print(f"[Stage 4] Competitors classified: {len(ctx.competitors)}")
    for c in ctx.competitors:
        print(f"          - {c.name} [{c.type}] threat={c.threat_level}")

    # No critical errors
    if ctx.errors:
        print(f"\nErrors recorded: {ctx.errors}")
    assert not ctx.errors, f"Pipeline had errors: {ctx.errors}"
