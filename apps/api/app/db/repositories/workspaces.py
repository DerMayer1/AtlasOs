from __future__ import annotations

from typing import Any

from app.db.client import get_client


async def create_workspace(user_id: str, input_data: dict) -> dict:
    client = await get_client()
    workspace_res = await client.table("workspaces").insert({
        "user_id": user_id,
        "name": input_data["name"],
        "company_name": input_data["company_name"],
        "website_url": input_data["website_url"],
        "description": input_data["description"],
        "target_market": input_data.get("target_market"),
    }).execute()
    workspace = workspace_res.data[0]

    await client.table("tracked_companies").insert({
        "workspace_id": workspace["id"],
        "name": workspace["company_name"],
        "website_url": workspace["website_url"],
        "type": "subject",
        "is_subject": True,
        "is_confirmed": True,
        "summary": workspace["description"],
    }).execute()
    return workspace


async def list_workspaces(user_id: str) -> list[dict]:
    client = await get_client()
    res = (
        await client.table("workspaces")
        .select("*")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return res.data


async def get_workspace(workspace_id: str, user_id: str) -> dict | None:
    client = await get_client()
    res = (
        await client.table("workspaces")
        .select("*")
        .eq("id", workspace_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return res.data


async def get_workspace_internal(workspace_id: str) -> dict | None:
    client = await get_client()
    res = (
        await client.table("workspaces")
        .select("*")
        .eq("id", workspace_id)
        .maybe_single()
        .execute()
    )
    return res.data


async def get_workspace_with_companies(workspace_id: str, user_id: str) -> dict | None:
    workspace = await get_workspace(workspace_id, user_id)
    if not workspace:
        return None
    companies = await list_tracked_companies(workspace_id)
    snapshots = await list_latest_snapshots(workspace_id)
    snapshots_by_company = {snapshot["company_id"]: snapshot for snapshot in snapshots}
    for company in companies:
        company["latest_snapshot"] = snapshots_by_company.get(company["id"])
    workspace["companies"] = companies
    return workspace


async def update_workspace(
    workspace_id: str,
    user_id: str,
    payload: dict[str, Any],
) -> dict | None:
    client = await get_client()
    res = (
        await client.table("workspaces")
        .update(payload)
        .eq("id", workspace_id)
        .eq("user_id", user_id)
        .execute()
    )
    return res.data[0] if res.data else None


async def update_workspace_status(
    workspace_id: str,
    status: str,
    *,
    error: str | None = None,
    category_label: str | None = None,
    category_definition: str | None = None,
) -> None:
    client = await get_client()
    payload: dict[str, Any] = {"status": status, "error": error}
    if category_label is not None:
        payload["category_label"] = category_label
    if category_definition is not None:
        payload["category_definition"] = category_definition
    await client.table("workspaces").update(payload).eq("id", workspace_id).execute()


async def delete_workspace(workspace_id: str, user_id: str) -> bool:
    client = await get_client()
    res = (
        await client.table("workspaces")
        .delete()
        .eq("id", workspace_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(res.data)


async def list_tracked_companies(workspace_id: str) -> list[dict]:
    client = await get_client()
    res = (
        await client.table("tracked_companies")
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("is_subject", desc=True)
        .order("created_at")
        .execute()
    )
    return res.data


async def list_confirmed_companies(workspace_id: str) -> list[dict]:
    client = await get_client()
    res = (
        await client.table("tracked_companies")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("is_confirmed", True)
        .order("is_subject", desc=True)
        .order("created_at")
        .execute()
    )
    return res.data


async def list_latest_snapshots(workspace_id: str) -> list[dict]:
    client = await get_client()
    res = (
        await client.table("company_snapshots")
        .select(
            "id,workspace_id,company_id,website_url,final_url,page_title,"
            "page_description,content_hash,metadata,captured_at"
        )
        .eq("workspace_id", workspace_id)
        .order("captured_at", desc=True)
        .execute()
    )
    latest: dict[str, dict] = {}
    for snapshot in res.data:
        latest.setdefault(snapshot["company_id"], snapshot)
    return list(latest.values())


async def list_snapshots(
    workspace_id: str,
    *,
    company_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    client = await get_client()
    query = (
        client.table("company_snapshots")
        .select(
            "id,workspace_id,company_id,website_url,final_url,page_title,"
            "page_description,content_hash,metadata,captured_at"
        )
        .eq("workspace_id", workspace_id)
    )
    if company_id:
        query = query.eq("company_id", company_id)
    res = await query.order("captured_at", desc=True).limit(limit).execute()
    return res.data


async def set_companies_monitoring_status(
    workspace_id: str,
    status: str,
    *,
    company_id: str | None = None,
    error: str | None = None,
) -> None:
    client = await get_client()
    payload: dict[str, Any] = {
        "monitoring_status": status,
        "snapshot_error": error,
    }
    query = client.table("tracked_companies").update(payload).eq(
        "workspace_id", workspace_id
    )
    if company_id:
        query = query.eq("id", company_id)
    else:
        query = query.eq("is_confirmed", True)
    await query.execute()


async def restore_companies_monitoring_status(workspace_id: str) -> None:
    client = await get_client()
    companies = await list_confirmed_companies(workspace_id)
    for company in companies:
        status = "ready" if company.get("last_snapshot_at") else "idle"
        await (
            client.table("tracked_companies")
            .update({
                "monitoring_status": status,
                "snapshot_error": None,
            })
            .eq("id", company["id"])
            .eq("workspace_id", workspace_id)
            .execute()
        )


async def create_company_snapshot(
    workspace_id: str,
    company_id: str,
    snapshot: dict,
) -> dict:
    client = await get_client()
    res = await client.table("company_snapshots").insert({
        "workspace_id": workspace_id,
        "company_id": company_id,
        **snapshot,
    }).execute()
    captured = res.data[0]
    await (
        client.table("tracked_companies")
        .update({
            "monitoring_status": "ready",
            "last_snapshot_at": captured["captured_at"],
            "snapshot_error": None,
        })
        .eq("id", company_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    return captured


async def replace_discovered_companies(workspace_id: str, competitors: list[dict]) -> None:
    client = await get_client()
    await (
        client.table("tracked_companies")
        .delete()
        .eq("workspace_id", workspace_id)
        .eq("is_subject", False)
        .execute()
    )
    if competitors:
        await client.table("tracked_companies").insert([
            {
                "workspace_id": workspace_id,
                "name": competitor["name"],
                "website_url": competitor.get("website"),
                "type": competitor["type"],
                "threat_level": competitor.get("threat_level"),
                "summary": competitor.get("summary"),
                "positioning": competitor.get("positioning"),
                "is_subject": False,
                "is_confirmed": False,
            }
            for competitor in competitors
        ]).execute()


async def confirm_tracked_companies(
    workspace_id: str,
    company_ids: list[str],
) -> list[dict]:
    client = await get_client()
    await (
        client.table("tracked_companies")
        .update({"is_confirmed": False})
        .eq("workspace_id", workspace_id)
        .eq("is_subject", False)
        .execute()
    )
    if company_ids:
        await (
            client.table("tracked_companies")
            .update({"is_confirmed": True})
            .eq("workspace_id", workspace_id)
            .in_("id", company_ids)
            .execute()
        )
    return await list_tracked_companies(workspace_id)
