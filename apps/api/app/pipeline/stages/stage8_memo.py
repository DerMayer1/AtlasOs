"""
Stage 8 — Memo Composer
Synthesizes the full pipeline output into a structured Market Memo in Markdown.
This is the final deliverable — formatted for executive presentation.
"""
from __future__ import annotations

import logging
from datetime import datetime

from openai import AsyncOpenAI

from app.config import settings
from app.pipeline.base import PipelineStage
from app.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a senior strategy consultant writing a market intelligence memo.
Write a complete, professional Market Memo in Markdown based on the analysis provided.

Structure the memo exactly as follows:
# Market Memo: [Company Name]
*[Category Label] — [Date]*

## Executive Summary
2-3 sentences capturing the key strategic insight.

## Market Category
Definition and context.

## Competitive Landscape
Summary of the competitive set, organized by type.

## Positioning Analysis
Description of where the company sits on the competitive map and what it means.

## Market Gaps
Each gap as a subsection with strategic implications.

## Strategic Recommendations
Each recommendation with rationale, expected impact, and key risk.

## Conclusion
One paragraph — the single most important thing to act on.

Tone: precise, direct, executive-level. No filler. No hedging. No bullet soup."""


def _build_context_summary(ctx: PipelineContext) -> str:
    parts = [
        f"Company: {ctx.input.company_name}",
        f"Description: {ctx.input.description}",
        f"Category: {ctx.category.label if ctx.category else 'Unknown'} — {ctx.category.definition if ctx.category else ''}",
        "",
        "COMPETITORS:",
        *[f"- {c.name} [{c.type}] threat={c.threat_level}: {c.summary}" for c in ctx.competitors],
        "",
        "POSITIONING MAP:",
        f"  X-axis: {ctx.positioning_map.x_axis['label'] if ctx.positioning_map else 'N/A'}",
        f"  Y-axis: {ctx.positioning_map.y_axis['label'] if ctx.positioning_map else 'N/A'}",
        "",
        "GAPS:",
        *[f"- {g.description} (addressability: {g.addressability})" for g in ctx.gaps],
        "",
        "RECOMMENDATIONS:",
        *[f"- [{r.type}] {r.description} | impact: {r.impact} | risk: {r.risk}" for r in ctx.recommendations],
    ]
    return "\n".join(parts)


class MemoComposerStage(PipelineStage):
    stage_number = 8
    stage_name = "Memo Composer"
    timeout_s = 15
    max_retries = 1  # Long output generation can timeout — one retry

    async def execute(self, ctx: PipelineContext) -> None:
        context_summary = _build_context_summary(ctx)
        date_str = datetime.utcnow().strftime("%B %Y")

        response = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.4,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Date: {date_str}\n\n{context_summary}"},
            ],
        )

        ctx.memo_markdown = response.choices[0].message.content or ""
        logger.info(f"[Stage 8] Memo composed — {len(ctx.memo_markdown)} chars")
