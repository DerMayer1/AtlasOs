from fastapi import APIRouter

router = APIRouter(tags=["auth"])


@router.post("/token/refresh")
async def refresh_token() -> dict:
    # Delegated to Supabase Auth — placeholder for BFF pattern
    return {}
