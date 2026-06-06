"""
Stage 2 — Category Classifier
Uses GPT-4o structured output to define the precise market category
the company operates in.
"""
from __future__ import annotations

import logging

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings
from app.pipeline.base import PipelineStage
from app.pipeline.context import Category, PipelineContext

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a market intelligence analyst specializing in B2B SaaS competitive positioning.
Your task is to define the precise market category for a company based on its description and website content.

Rules:
- Be specific. Avoid generic labels like "AI software" or "SaaS platform".
- Use the language of practitioners, not marketers.
- The definition should describe what the category does, not what the company does.
- 1-2 sentences maximum for the definition."""


class CategoryOutput(BaseModel):
    label: str
    definition: str


class CategoryClassifierStage(PipelineStage):
    stage_number = 2
    stage_name = "Category Classifier"
    timeout_s = 10

    async def execute(self, ctx: PipelineContext) -> None:
        user_content = f"""Company: {ctx.input.company_name}
Description: {ctx.input.description}
Website content (excerpt): {ctx.raw_text[:3000] if ctx.raw_text else "Not available"}
Target market: {ctx.input.target_market or "Not specified"}"""

        response = await client.beta.chat.completions.parse(
            model="gpt-4o",
            temperature=0.2,
            max_tokens=300,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format=CategoryOutput,
        )

        result = response.choices[0].message.parsed
        if result:
            ctx.category = Category(label=result.label, definition=result.definition)
            logger.info(f"[Stage 2] Category: {ctx.category.label}")
