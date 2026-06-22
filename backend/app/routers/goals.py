from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/", include_in_schema=False)
async def goals_not_implemented():
    """Placeholder — implementado na Sprint 15."""
    return JSONResponse(
        status_code=501,
        content={
            "detail": "Módulo de Metas ainda não implementado.",
            "sprint": "Sprint 15",
        },
    )
