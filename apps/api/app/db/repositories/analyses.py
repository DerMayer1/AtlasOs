from __future__ import annotations

from typing import Any

from app.db.client import get_client


async def create_analysis(user_id: str, input_data: dict, depth: str = "standard") -> dict:
    client = await get_client()
    res = await client.table("analyses").insert({
        "user_id": user_id,
        "status": "pending",
        "depth": depth,
        "input": input_data,
    }).execute()
    return res.data[0]


async def get_analysis(analysis_id: str, user_id: str) -> dict | None:
    client = await get_client()
    res = (
        await client.table("analyses")
        .select("*")
        .eq("id", analysis_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    return res.data


async def list_analyses(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> tuple[list[dict], int]:
    client = await get_client()
    query = (
        client.table("analyses")
        .select("id, status, input, created_at, completed_at, duration_ms", count="exact")
        .eq("user_id", user_id)
    )
    if status:
        query = query.eq("status", status)
    res = await query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    items = [
        {
            **record,
            "company_name": record.get("input", {}).get("company_name", ""),
        }
        for record in res.data
    ]
    return items, res.count or 0


async def update_analysis_status(
    analysis_id: str,
    status: str,
    result: dict | None = None,
    error: str | None = None,
    duration_ms: int | None = None,
) -> None:
    client = await get_client()
    payload: dict[str, Any] = {"status": status}
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error[:2000]  # Truncate long error messages
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    if status in ("complete", "failed"):
        from datetime import datetime, timezone
        payload["completed_at"] = datetime.now(timezone.utc).isoformat()
    await client.table("analyses").update(payload).eq("id", analysis_id).execute()


async def delete_analysis(analysis_id: str, user_id: str) -> bool:
    client = await get_client()
    res = await client.table("analyses").delete().eq("id", analysis_id).eq("user_id", user_id).execute()
    return len(res.data) > 0


async def count_active_analyses(user_id: str) -> int:
    """Returns count of pending + running analyses for a user."""
    client = await get_client()
    res = (
        await client.table("analyses")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .in_("status", ["pending", "running"])
        .execute()
    )
    return res.count or 0
