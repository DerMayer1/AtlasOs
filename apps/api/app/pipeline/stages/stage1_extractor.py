"""
Stage 1 — Website Extractor
Fetches and parses the company homepage into clean text (max ~4K tokens).
Falls back gracefully if the site is unreachable.
"""
from __future__ import annotations

import logging

import httpx

from app.pipeline.base import PipelineStage
from app.pipeline.context import PipelineContext
from app.pipeline.website import MAX_RESPONSE_BYTES, extract_text, is_safe_url

logger = logging.getLogger(__name__)


class WebsiteExtractorStage(PipelineStage):
    stage_number = 1
    stage_name = "Website Extractor"
    timeout_s = 15

    async def execute(self, ctx: PipelineContext) -> None:
        url = ctx.input.website_url

        if not is_safe_url(url):
            logger.warning(f"[Stage 1] Blocked unsafe URL: {url}")
            ctx.raw_text = ""
            return

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=10.0,
                headers={"User-Agent": "AtlasOS/1.0 (market intelligence research bot)"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Cap response size before parsing — prevent memory issues on huge pages
                content = response.content[:MAX_RESPONSE_BYTES].decode("utf-8", errors="replace")
                ctx.raw_text = extract_text(content)
                logger.info(f"[Stage 1] Extracted {len(ctx.raw_text)} chars from {url}")

        except httpx.HTTPStatusError as e:
            logger.warning(f"[Stage 1] HTTP {e.response.status_code} for {url} — continuing without site content")
            ctx.raw_text = ""
        except Exception as e:
            logger.warning(f"[Stage 1] Extraction failed for {url}: {e} — continuing without site content")
            ctx.raw_text = ""
