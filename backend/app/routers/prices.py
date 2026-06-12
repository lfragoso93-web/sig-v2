from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.asset import AssetType
from app.models.user import User
from app.services.price_history_service import get_price_history

router = APIRouter()


@router.get("/{ticker}/history")
async def price_history(
    ticker: str,
    asset_type: str = Query("ACAO", description="Tipo do ativo (ex: ACAO, FII, STOCK)"),
    days: int = Query(90, ge=7, le=730, description="Quantos dias de historico retornar"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """
    Retorna historico de precos de fechamento do banco.
    Se os dados estiverem desatualizados, busca automaticamente antes de retornar.

    Exemplo: GET /api/v1/prices/PETR4/history?asset_type=ACAO&days=90
    """
    try:
        at = AssetType(asset_type.upper())
    except ValueError:
        at = AssetType.ACAO

    data = await get_price_history(db, ticker.upper(), at, days=days)
    return {"ticker": ticker.upper(), "asset_type": at.value, "days": days, "data": data}
