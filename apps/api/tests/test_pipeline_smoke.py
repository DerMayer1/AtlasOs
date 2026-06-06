"""
Smoke test — runs all 8 stages against a real company.
Requires OPENAI_API_KEY and TAVILY_API_KEY in root .env
Run: pytest tests/test_pipeline_smoke.py -v -s
"""
import pytest
from app.pipeline.context import CompanyInput
from app.pipeline.runner import run_pipeline


@pytest.mark.asyncio
async def test_full_pipeline_linear():
    company = CompanyInput(
        company_name="Linear",
        website_url="https://linear.app",
        description="Linear is a project management tool built for modern software teams. It helps teams plan, track, and ship product work.",
        target_market="B2B SaaS, software engineering teams",
        known_competitors=["Jira", "Asana"],
        analysis_depth="standard",
    )

    ctx = await run_pipeline(company)

    print(f"\n{'='*60}")
    print("PIPELINE RESULTS — Linear")
    print('='*60)

    # Stage 1
    assert ctx.raw_text, "Stage 1: raw_text should not be empty"
    print(f"\n[Stage 1] Extracted {len(ctx.raw_text)} chars")

    # Stage 2
    assert ctx.category is not None, "Stage 2: category should be set"
    print(f"\n[Stage 2] Category: {ctx.category.label}")
    print(f"          {ctx.category.definition}")

    # Stage 3
    assert len(ctx.search_results) > 0, "Stage 3: should return search results"
    print(f"\n[Stage 3] Search results: {len(ctx.search_results)}")

    # Stage 4
    assert len(ctx.competitors) > 0, "Stage 4: should classify at least one competitor"
    print(f"\n[Stage 4] Competitors: {len(ctx.competitors)}")
    for c in ctx.competitors:
        print(f"          - {c.name} [{c.type}] threat={c.threat_level}")

    # Stage 5
    assert ctx.positioning_map is not None, "Stage 5: positioning map should be set"
    pm = ctx.positioning_map
    print(f"\n[Stage 5] Axes: {pm.x_axis['label']} / {pm.y_axis['label']}")
    print(f"          Entities plotted: {len(pm.entities)}")

    # Stage 6
    assert len(ctx.gaps) > 0, "Stage 6: should identify at least one gap"
    print(f"\n[Stage 6] Gaps: {len(ctx.gaps)}")
    for g in ctx.gaps:
        print(f"          - {g.description[:80]}...")

    # Stage 7
    assert len(ctx.recommendations) > 0, "Stage 7: should produce at least one recommendation"
    print(f"\n[Stage 7] Recommendations: {len(ctx.recommendations)}")
    for r in ctx.recommendations:
        print(f"          - [{r.type}] {r.description[:80]}...")

    # Stage 8
    assert ctx.memo_markdown, "Stage 8: memo should not be empty"
    assert len(ctx.memo_markdown) > 500, "Stage 8: memo seems too short"
    print(f"\n[Stage 8] Memo: {len(ctx.memo_markdown)} chars")
    print(f"\n{'='*60}")
    print("MEMO PREVIEW (first 400 chars):")
    print(ctx.memo_markdown[:400])
    print('='*60)

    # No errors
    if ctx.errors:
        print(f"\nErrors: {ctx.errors}")
    assert not ctx.errors, f"Pipeline had errors: {ctx.errors}"
