from __future__ import annotations

from app.db.client import get_client


async def create_memo(analysis_id: str, content_md: str) -> dict:
    client = await get_client()
    res = await client.table("memos").insert({
        "analysis_id": analysis_id,
        "content_md": content_md,
    }).execute()
    return res.data[0]


async def get_memo_by_analysis(analysis_id: str) -> dict | None:
    client = await get_client()
    res = await client.table("memos").select("*").eq("analysis_id", analysis_id).single().execute()
    return res.data


async def increment_export_count(memo_id: str) -> None:
    client = await get_client()
    await client.rpc("increment_export_count", {"memo_id": memo_id}).execute()
