from fastapi import APIRouter

router = APIRouter(tags=["analyses"])


@router.get("")
async def list_analyses() -> dict:
    return {"items": [], "total": 0}


@router.post("")
async def create_analysis() -> dict:
    return {}


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str) -> dict:
    return {}


@router.delete("/{analysis_id}")
async def delete_analysis(analysis_id: str) -> dict:
    return {}


@router.get("/{analysis_id}/stream")
async def stream_analysis(analysis_id: str) -> dict:
    return {}


@router.get("/{analysis_id}/memo")
async def get_memo(analysis_id: str) -> dict:
    return {}


@router.post("/{analysis_id}/memo/export")
async def export_memo(analysis_id: str) -> dict:
    return {}
