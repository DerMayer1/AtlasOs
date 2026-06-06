"""
Stage 7 — Recommendation Engine
Produces 3 prioritized strategic moves based on gaps and competitive landscape.
"""
from __future__ import annotations

import logging

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings
from app.pipeline.base import PipelineStage
from app.pipeline.context import PipelineContext, Recommendation
from app.pipeline.validator import validate_recommendations

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a B2B SaaS strategy advisor.
Based on a company's competitive landscape and identified market gaps,
produce exactly 3 prioritized strategic recommendations.

Each recommendation must be one of these types:
- Reposition: shift how the product is perceived or marketed
- Vertically Focus: go deep in one segment instead of wide
- Category Create: define and own a new market category
- Competitive Response: directly address a specific competitive threat

For each recommendation:
- Be concrete and actionable, not generic
- Quantify expected impact where possible
- Identify the primary execution risk
- Order them from highest to lowest strategic priority"""


class RecommendationItem(BaseModel):
    type: str
    description: str
    impact: str
    risk: str


class RecommendationOutput(BaseModel):
    recommendations: list[RecommendationItem]


class RecommendationEngineStage(PipelineStage):
    stage_number = 7
    stage_name = "Recommendation Engine"
    timeout_s = 8
    max_retries = 1

    async def execute(self, ctx: PipelineContext) -> None:
        gaps_text = "\n".join(f"- {g.description}" for g in ctx.gaps) if ctx.gaps else "No gaps identified."
        competitors_text = "\n".join(
            f"- {c.name} [{c.type}] threat={c.threat_level}: {c.positioning}"
            for c in ctx.competitors[:8]
        ) if ctx.competitors else "No competitors identified."

        user_content = f"""Company: {ctx.input.company_name}
Description: {ctx.input.description}
Category: {ctx.category.label if ctx.category else 'Unknown'}

Key competitors:
{competitors_text}

Identified market gaps:
{gaps_text}

Produce 3 prioritized strategic recommendations."""

        response = await client.beta.chat.completions.parse(
            model="gpt-4o",
            temperature=0.5,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=RecommendationOutput,
        )

        result = response.choices[0].message.parsed
        if result:
            raw = [
                Recommendation(type=r.type, description=r.description, impact=r.impact, risk=r.risk)
                for r in result.recommendations
            ]
            ctx.recommendations = validate_recommendations(raw)
            logger.info(f"[Stage 7] Generated {len(ctx.recommendations)} recommendations")
