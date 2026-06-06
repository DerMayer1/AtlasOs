"""
Stage 1 — Website Extractor
Fetches and parses the company homepage into clean text (max ~4K tokens).
Falls back gracefully if the site is unreachable.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.pipeline.base import PipelineStage
from app.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)

MAX_CHARS = 16_000  # ~4K tokens


def _is_safe_url(url: str) -> bool:
    """Basic SSRF protection — block private/internal ranges."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    blocked = [
        "localhost", "127.", "0.0.0.0", "169.254.",  # loopback / link-local
        "10.", "172.16.", "192.168.",                  # RFC-1918 private ranges
        "::1", "fe80:",                                # IPv6 loopback / link-local
    ]
    return not any(host.startswith(b) for b in blocked)


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "img"]):
        tag.decompose()

    # Prioritize meaningful content blocks
    priority_tags = soup.find_all(["h1", "h2", "h3", "p", "li", "article", "section", "main"])
    if priority_tags:
        text = " ".join(t.get_text(separator=" ", strip=True) for t in priority_tags)
    else:
        text = soup.get_text(separator=" ", strip=True)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_CHARS]


class WebsiteExtractorStage(PipelineStage):
    stage_number = 1
    stage_name = "Website Extractor"
    timeout_s = 15

    async def execute(self, ctx: PipelineContext) -> None:
        url = ctx.input.website_url

        if not _is_safe_url(url):
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
                ctx.raw_text = _extract_text(response.text)
                logger.info(f"[Stage 1] Extracted {len(ctx.raw_text)} chars from {url}")

        except httpx.HTTPStatusError as e:
            logger.warning(f"[Stage 1] HTTP {e.response.status_code} for {url} — continuing without site content")
            ctx.raw_text = ""
        except Exception as e:
            logger.warning(f"[Stage 1] Extraction failed for {url}: {e} — continuing without site content")
            ctx.raw_text = ""
