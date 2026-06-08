from fastapi import APIRouter
from app.integrations.fx_rate import get_usd_brl

router = APIRouter(prefix="/api/v1/fx", tags=["fx"])


@router.get("/usd-brl")
async def usd_brl_rate():
    """Retorna cotacao atual USD/BRL para uso no formulario."""
    rate = await get_usd_brl()
    return {"rate": rate, "pair": "USDBRL"}
