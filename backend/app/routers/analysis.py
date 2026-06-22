from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/", include_in_schema=False)
async def analysis_not_implemented():
    """Placeholder — implementado na Sprint 13."""
    return JSONResponse(
        status_code=501,
        content={
            "detail": "Módulo de Análise ainda não implementado.",
            "sprint": "Sprint 13",
        },
    )
