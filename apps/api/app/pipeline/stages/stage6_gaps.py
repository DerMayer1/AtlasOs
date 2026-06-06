"""
Stage 6 — Gap Detector
Identifies 2-5 underserved positions in the market based on
the positioning map and competitive landscape.
"""
from __future__ import annotations

import logging

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings
from app.pipeline.base import PipelineStage
from app.pipeline.context import Gap, PipelineContext

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a market strategy analyst specializing in competitive gap analysis.
Given a positioning map with competitors plotted on two axes, identify underserved
positions in the market — quadrants or zones where no strong player exists
but real customer demand likely does.

For each gap:
- Be specific about the unmet need, not just the empty quadrant
- Assess how addressable this gap is (market size, willingness to pay, accessibility)
- Identify the primary risk of pursuing it
- Return 2 to 5 gaps, ordered by strategic attractiveness"""


class GapItem(BaseModel):
    description: str
    addressability: str
    risk: str


class GapOutput(BaseModel):
    gaps: list[GapItem]


class GapDetectorStage(PipelineStage):
    stage_number = 6
    stage_name = "Gap Detector"
    timeout_s = 8

    async def execute(self, ctx: PipelineContext) -> None:
        if not ctx.positioning_map:
            logger.warning("[Stage 6] No positioning map available")
            return

        pm = ctx.positioning_map
        entities_text = "\n".join(
            f"- {'[SUBJECT] ' if e.is_subject else ''}{e.name}: x={e.x:.2f}, y={e.y:.2f}"
            for e in pm.entities
        )

        user_content = f"""Subject company: {ctx.input.company_name}
Category: {ctx.category.label if ctx.category else 'Unknown'}

Positioning map axes:
  X: {pm.x_axis['label']} (left={pm.x_axis['low']}, right={pm.x_axis['high']})
  Y: {pm.y_axis['label']} (bottom={pm.y_axis['low']}, top={pm.y_axis['high']})

Entities plotted:
{entities_text}

Identify the underserved gaps in this competitive landscape."""

        response = await client.beta.chat.completions.parse(
            model="gpt-4o",
            temperature=0.4,
            max_tokens=1200,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=GapOutput,
        )

        result = response.choices[0].message.parsed
        if result:
            ctx.gaps = [Gap(description=g.description, addressability=g.addressability, risk=g.risk) for g in result.gaps]
            logger.info(f"[Stage 6] Identified {len(ctx.gaps)} market gaps")
