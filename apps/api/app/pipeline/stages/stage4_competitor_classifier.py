"""
Stage 4 — Competitor Classifier
Uses GPT-4o to classify each search result into one of 5 competitor types
and assign a threat level.
"""
from __future__ import annotations

import logging

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings
from app.pipeline.base import PipelineStage
from app.pipeline.context import Competitor, PipelineContext
from app.pipeline.validator import validate_competitors

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a competitive intelligence analyst.
Given a subject company and a list of companies found via web search,
classify each one relative to the subject company.

Competitor types:
- direct: same category, same target customer, similar feature set
- indirect: different approach or category, but competes for same budget/outcome
- substitute: different product entirely, but solves the same underlying problem
- adjacent: operates nearby in the market, potential future competitor
- future: not a competitor today, but trajectory suggests collision within 2 years

Threat levels:
- high: strong overlap, well-funded, actively targeting same customers
- medium: partial overlap or early-stage threat
- low: minimal overlap today

Only include companies that are genuinely relevant. Skip news articles, blogs, and review sites."""


class CompetitorItem(BaseModel):
    name: str
    website: str | None
    type: str
    threat_level: str
    summary: str
    positioning: str


class CompetitorListOutput(BaseModel):
    competitors: list[CompetitorItem]


class CompetitorClassifierStage(PipelineStage):
    stage_number = 4
    stage_name = "Competitor Classifier"
    timeout_s = 12
    is_critical = True  # No competitors → no positioning → abort

    async def execute(self, ctx: PipelineContext) -> None:
        if not ctx.search_results:
            raise ValueError("No competitor search results were found")

        search_text = "\n".join(
            f"- {r['title']} | {r['url']}\n  {r['content']}"
            for r in ctx.search_results
        )

        user_content = f"""Subject company: {ctx.input.company_name}
Category: {ctx.category.label if ctx.category else ctx.input.description}
Description: {ctx.input.description}

Search results to classify:
{search_text}

Also include these known competitors if not already in the list: {ctx.input.known_competitors}"""

        response = await client.beta.chat.completions.parse(
            model="gpt-4o",
            temperature=0.2,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=CompetitorListOutput,
        )

        result = response.choices[0].message.parsed
        if result:
            raw = [
                Competitor(
                    name=c.name,
                    website=c.website,
                    type=c.type,
                    threat_level=c.threat_level,
                    summary=c.summary,
                    positioning=c.positioning,
                )
                for c in result.competitors
            ]
            ctx.competitors = validate_competitors(raw)
            if not ctx.competitors:
                raise ValueError("No valid competitors were identified")
            logger.info(
                f"[Stage 4] Classified {len(ctx.competitors)} competitors "
                "(after dedup/validation)"
            )
        else:
            raise ValueError("LLM returned empty competitor output")
