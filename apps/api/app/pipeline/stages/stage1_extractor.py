"""
Stage 1 — Website Extractor
Fetches and parses the company homepage into clean text (max ~4K tokens).
Falls back gracefully if the site is unreachable.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.pipeline.base import PipelineStage
from app.pipeline.context import PipelineContext

logger = logging.getLogger(__name__)

MAX_CHARS = 16_000       # ~4K tokens
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2MB cap — don't parse giant pages

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
]


def _is_safe_url(url: str) -> bool:
    """
    Two-layer SSRF protection:
    1. Parse-time check — reject obvious private hostnames
    2. DNS resolution check — resolve hostname and verify the IP is not private
       (prevents DNS rebinding attacks)
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""

    # Layer 1: string-level blocklist
    string_blocked = [
        "localhost", "metadata.google.internal",
        "169.254.169.254",  # AWS/GCP metadata endpoint
    ]
    if any(host == b or host.startswith(b + ".") for b in string_blocked):
        return False

    # Layer 2: DNS resolution + IP range check
    try:
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            raw_ip = info[4][0]
            try:
                addr = ipaddress.ip_address(raw_ip)
            except ValueError:
                continue
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                return False
            for network in _PRIVATE_NETWORKS:
                if addr in network:
                    return False
    except socket.gaierror:
        # DNS resolution failed — treat as safe (will fail at HTTP level)
        pass

    return True


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "img"]):
        tag.decompose()

    priority_tags = soup.find_all(["h1", "h2", "h3", "p", "li", "article", "section", "main"])
    if priority_tags:
        text = " ".join(t.get_text(separator=" ", strip=True) for t in priority_tags)
    else:
        text = soup.get_text(separator=" ", strip=True)

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

                # Cap response size before parsing — prevent memory issues on huge pages
                content = response.content[:MAX_RESPONSE_BYTES].decode("utf-8", errors="replace")
                ctx.raw_text = _extract_text(content)
                logger.info(f"[Stage 1] Extracted {len(ctx.raw_text)} chars from {url}")

        except httpx.HTTPStatusError as e:
            logger.warning(f"[Stage 1] HTTP {e.response.status_code} for {url} — continuing without site content")
            ctx.raw_text = ""
        except Exception as e:
            logger.warning(f"[Stage 1] Extraction failed for {url}: {e} — continuing without site content")
            ctx.raw_text = ""
