from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.fx_rate_reader import load_latest_usd_brl_rate

router = APIRouter(tags=["fx"])


@router.get("/usd-brl")
async def usd_brl_rate(db: AsyncSession = Depends(get_db)):
    """Retorna a última cotação USD/BRL persistida no banco."""

    persisted = await load_latest_usd_brl_rate(db)
    if persisted is None:
        raise HTTPException(
            status_code=503,
            detail="Cotação USD/BRL persistida indisponível.",
        )
    return {
        "rate": float(persisted.rate),
        "pair": "USDBRL",
        "rate_date": persisted.rate_date.isoformat(),
        "source": "persisted_fx_rates",
    }
