from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.treasury_service import list_treasury

router = APIRouter(prefix="/portfolios/{portfolio_id}/treasury", tags=["treasury"])


@router.get("/")
async def list_treasury_investments(
    portfolio_id: int,
    only_active: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista as posicoes de Tesouro Direto da carteira.

    Lotes sao derivados das transacoes com asset_type = 'tesouro_direto'.
    Cada lote retorna: ticker, purchase_price, quantity, invested_value,
    valor_atual, lucro_prejuizo, rentabilidade_pct.
    """
    return await list_treasury(db, portfolio_id, current_user.id, only_active)
