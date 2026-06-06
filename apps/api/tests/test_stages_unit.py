"""
Unit tests for pipeline stages 1-4.
All LLM and external calls are mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.pipeline.context import CompanyInput, PipelineContext


def make_ctx(url: str = "https://example.com") -> PipelineContext:
    return PipelineContext(
        input=CompanyInput(
            company_name="TestCo",
            website_url=url,
            description="A B2B SaaS product for testing.",
            analysis_depth="standard",
        )
    )


# ── Stage 1 ──────────────────────────────────────────────────────────────────

class TestWebsiteExtractor:
    @pytest.mark.asyncio
    async def test_extracts_text_from_valid_response(self):
        from app.pipeline.stages.stage1_extractor import WebsiteExtractorStage

        mock_response = MagicMock()
        html = "<html><body><h1>Hello</h1><p>World product description</p></body></html>"
        mock_response.content = html.encode("utf-8")
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            ctx = make_ctx()
            stage = WebsiteExtractorStage()
            await stage.execute(ctx)

            assert "Hello" in ctx.raw_text
            assert "World product description" in ctx.raw_text

    @pytest.mark.asyncio
    async def test_blocks_ssrf_localhost(self):
        from app.pipeline.stages.stage1_extractor import WebsiteExtractorStage

        ctx = make_ctx("http://localhost/admin")
        stage = WebsiteExtractorStage()
        await stage.execute(ctx)
        assert ctx.raw_text == ""

    @pytest.mark.asyncio
    async def test_blocks_ssrf_private_ip(self):
        from app.pipeline.stages.stage1_extractor import WebsiteExtractorStage

        ctx = make_ctx("http://192.168.1.1/secret")
        stage = WebsiteExtractorStage()
        await stage.execute(ctx)
        assert ctx.raw_text == ""

    @pytest.mark.asyncio
    async def test_graceful_failure_on_http_error(self):
        import httpx
        from app.pipeline.stages.stage1_extractor import WebsiteExtractorStage

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError("403", request=MagicMock(), response=mock_response)
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            ctx = make_ctx()
            stage = WebsiteExtractorStage()
            await stage.execute(ctx)
            assert ctx.raw_text == ""


# ── Stage 2 ──────────────────────────────────────────────────────────────────

class TestCategoryClassifier:
    @pytest.mark.asyncio
    async def test_sets_category_from_llm_response(self):
        from app.pipeline.stages.stage2_classifier import CategoryClassifierStage

        mock_parsed = MagicMock()
        mock_parsed.label = "B2B project tracking tools"
        mock_parsed.definition = "Software for planning and tracking engineering work."

        mock_choice = MagicMock()
        mock_choice.message.parsed = mock_parsed
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("app.pipeline.stages.stage2_classifier.client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
            ctx = make_ctx()
            ctx.raw_text = "We build tools for software teams."
            stage = CategoryClassifierStage()
            await stage.execute(ctx)

            assert ctx.category is not None
            assert ctx.category.label == "B2B project tracking tools"
            assert "engineering" in ctx.category.definition


# ── Stage 4 ──────────────────────────────────────────────────────────────────

class TestCompetitorClassifier:
    @pytest.mark.asyncio
    async def test_skips_when_no_search_results(self):
        from app.pipeline.stages.stage4_competitor_classifier import CompetitorClassifierStage

        ctx = make_ctx()
        ctx.search_results = []
        stage = CompetitorClassifierStage()
        await stage.execute(ctx)
        assert ctx.competitors == []

    @pytest.mark.asyncio
    async def test_classifies_competitors(self):
        from app.pipeline.context import Category
        from app.pipeline.stages.stage4_competitor_classifier import CompetitorClassifierStage

        mock_competitor = MagicMock()
        mock_competitor.name = "Jira"
        mock_competitor.website = "https://atlassian.com/jira"
        mock_competitor.type = "direct"
        mock_competitor.threat_level = "high"
        mock_competitor.summary = "Market leader in project tracking."
        mock_competitor.positioning = "Enterprise-focused, complex UX."

        mock_parsed = MagicMock()
        mock_parsed.competitors = [mock_competitor]
        mock_choice = MagicMock()
        mock_choice.message.parsed = mock_parsed
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("app.pipeline.stages.stage4_competitor_classifier.client") as mock_client:
            mock_client.beta.chat.completions.parse = AsyncMock(return_value=mock_response)
            ctx = make_ctx()
            ctx.category = Category(label="Project tracking", definition="Tools for PM.")
            ctx.search_results = [{"title": "Jira", "url": "https://jira.com", "content": "Project management"}]
            stage = CompetitorClassifierStage()
            await stage.execute(ctx)

            assert len(ctx.competitors) == 1
            assert ctx.competitors[0].name == "Jira"
            assert ctx.competitors[0].type == "direct"
