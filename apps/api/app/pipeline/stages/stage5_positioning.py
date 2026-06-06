"""
Stage 5 — Positioning Analyzer
Uses GPT-4o to determine two strategic axes and plot all competitors
+ the subject company on a 2x2 matrix.
"""
from __future__ import annotations

import logging

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings
from app.pipeline.base import PipelineStage
from app.pipeline.context import PipelineContext, PositioningEntity, PositioningMap
from app.pipeline.validator import validate_positioning_map

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a market positioning strategist.
Given a company and its competitive landscape, define two strategic axes
that best differentiate the competitors from each other and from the subject company.

Axis rules:
- Choose axes that are strategically meaningful, not just descriptive
- Examples: "SMB vs Enterprise", "Manual vs Automated", "Narrow vs Broad", "Point Solution vs Platform"
- Avoid generic axes like "Good vs Bad" or "Cheap vs Expensive"

Coordinate rules:
- x and y values must be between -1.0 and 1.0
- Place the subject company accurately relative to competitors
- Spread entities across the quadrants — avoid clustering everything in one area"""


class AxisSchema(BaseModel):
    label: str
    low: str
    high: str


class EntitySchema(BaseModel):
    name: str
    x: float
    y: float
    is_subject: bool


class PositioningOutput(BaseModel):
    x_axis: AxisSchema
    y_axis: AxisSchema
    entities: list[EntitySchema]


class PositioningAnalyzerStage(PipelineStage):
    stage_number = 5
    stage_name = "Positioning Analyzer"
    timeout_s = 10

    async def execute(self, ctx: PipelineContext) -> None:
        if not ctx.competitors:
            logger.warning("[Stage 5] No competitors to position")
            return

        competitors_text = "\n".join(
            f"- {c.name}: {c.summary} (type={c.type}, threat={c.threat_level})"
            for c in ctx.competitors
        )

        user_content = f"""Subject company: {ctx.input.company_name}
Description: {ctx.input.description}
Category: {ctx.category.label if ctx.category else 'Unknown'}

Competitors:
{competitors_text}

Define two strategic axes and plot every competitor + the subject company."""

        response = await client.beta.chat.completions.parse(
            model="gpt-4o",
            temperature=0.3,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=PositioningOutput,
        )

        result = response.choices[0].message.parsed
        if result:
            pm = PositioningMap(
                x_axis={"label": result.x_axis.label, "low": result.x_axis.low, "high": result.x_axis.high},
                y_axis={"label": result.y_axis.label, "low": result.y_axis.low, "high": result.y_axis.high},
                entities=[
                    PositioningEntity(name=e.name, x=e.x, y=e.y, is_subject=e.is_subject)
                    for e in result.entities
                ],
            )
            ctx.positioning_map = validate_positioning_map(pm)
            logger.info(f"[Stage 5] Axes: {result.x_axis.label} / {result.y_axis.label}")
