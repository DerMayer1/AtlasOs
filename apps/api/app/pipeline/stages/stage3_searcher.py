"""
Stage 3 — Competitor Searcher
Uses Tavily to find competitors based on category + description.
Returns up to 10 structured search results for Stage 4 to classify.
"""
from __future__ import annotations

import logging

from tavily import AsyncTavilyClient

from app.config import settings
from app.pipeline.base import PipelineStage
from app.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)

client = AsyncTavilyClient(api_key=settings.tavily_api_key)


def _build_queries(ctx: PipelineContext) -> list[str]:
    category = ctx.category.label if ctx.category else ctx.input.description
    name = ctx.input.company_name
    queries = [
        f"{category} software companies competitors alternatives",
        f"best {category} tools {ctx.input.target_market or 'B2B'} 2024 2025",
    ]
    if ctx.input.known_competitors:
        # Enrich known competitors with context
        queries.append(f"{' '.join(ctx.input.known_competitors[:3])} {category} comparison")
    return queries


class CompetitorSearcherStage(PipelineStage):
    stage_number = 3
    stage_name = "Competitor Searcher"
    timeout_s = 15

    async def execute(self, ctx: PipelineContext) -> None:
        queries = _build_queries(ctx)
        all_results: list[dict] = []
        seen_urls: set[str] = set()

        for query in queries:
            try:
                response = await client.search(
                    query=query,
                    search_depth="basic",
                    max_results=5,
                    include_answer=False,
                )
                for r in response.get("results", []):
                    url = r.get("url", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "title":   r.get("title", ""),
                            "url":     url,
                            "content": r.get("content", "")[:500],
                        })
            except Exception as e:
                logger.warning(f"[Stage 3] Search failed for query '{query}': {e}")

        ctx.search_results = all_results[:10]
        logger.info(f"[Stage 3] Found {len(ctx.search_results)} results")
