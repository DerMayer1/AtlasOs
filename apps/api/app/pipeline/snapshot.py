from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

import httpx
from bs4 import BeautifulSoup

from app.pipeline.website import MAX_RESPONSE_BYTES, extract_text, is_safe_url


@dataclass(frozen=True)
class WebsiteSnapshot:
    website_url: str
    final_url: str
    page_title: str | None
    page_description: str | None
    content_hash: str
    content_text: str
    metadata: dict[str, int | str]

    def to_record(self) -> dict:
        return asdict(self)


def build_snapshot(
    *,
    website_url: str,
    final_url: str,
    html: str,
    status_code: int,
) -> WebsiteSnapshot:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else None
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = (
        description_tag.get("content", "").strip()
        if description_tag and description_tag.get("content")
        else None
    )
    content_text = extract_text(html)
    content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

    return WebsiteSnapshot(
        website_url=website_url,
        final_url=final_url,
        page_title=title,
        page_description=description,
        content_hash=content_hash,
        content_text=content_text,
        metadata={
            "status_code": status_code,
            "character_count": len(content_text),
        },
    )


async def capture_website_snapshot(url: str) -> WebsiteSnapshot:
    if not is_safe_url(url):
        raise ValueError("Website URL resolves to a private or unsafe network.")

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=15.0,
        headers={"User-Agent": "AtlasOS/1.0 (market monitoring bot)"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    html = response.content[:MAX_RESPONSE_BYTES].decode("utf-8", errors="replace")
    snapshot = build_snapshot(
        website_url=url,
        final_url=str(response.url),
        html=html,
        status_code=response.status_code,
    )
    if not snapshot.content_text:
        raise ValueError("Website returned no monitorable text content.")
    return snapshot
