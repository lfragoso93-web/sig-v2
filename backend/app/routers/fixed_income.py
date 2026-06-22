from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/", include_in_schema=False)
async def fixed_income_not_implemented():
    """Placeholder — implementado na Sprint 14."""
    return JSONResponse(
        status_code=501,
        content={
            "detail": "Módulo de Renda Fixa ainda não implementado.",
            "sprint": "Sprint 14",
        },
    )
