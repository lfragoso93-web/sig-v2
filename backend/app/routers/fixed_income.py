from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/", include_in_schema=False)
async def fixed_income_not_implemented():
    """Placeholder de API; o domínio financeiro já possui serviços canônicos próprios."""
    return JSONResponse(
        status_code=501,
        content={
            "detail": "Superfície dedicada de Renda Fixa ainda não implementada.",
            "status": "api_placeholder",
        },
    )
