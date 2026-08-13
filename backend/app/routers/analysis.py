from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/", include_in_schema=False)
async def analysis_not_implemented():
    """Placeholder preservado até o macroprojeto arquitetural #246 + #57."""
    return JSONResponse(
        status_code=501,
        content={
            "detail": "Módulo de Análise ainda não implementado.",
            "status": "planned_with_goals_redesign",
        },
    )
