"""
dividend_service.py
-------------------
Operacoes de leitura e resumo de proventos de carteira.
O Dividend agora referencia AssetDividend (global) + portfolio_id.
Chave: (portfolio_id, asset_dividend_id).
"""
import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus

logger = logging.getLogger(__name__)


async def list_dividends(
    db: AsyncSession,
    portfolio_id: int,
    asset_id: Optional[int] = None,
    year: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Dividend], int]:
    """
    Lista proventos de uma carteira com filtros opcionais.
    Faz join com AssetDividend para expor ex_date, payment_date, etc.
    """
    stmt = (
        select(Dividend)
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .where(Dividend.portfolio_id == portfolio_id)
    )
    count_stmt = (
        select(func.count())
        .select_from(Dividend)
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .where(Dividend.portfolio_id == portfolio_id)
    )

    if asset_id:
        stmt       = stmt.where(AssetDividend.asset_id == asset_id)
        count_stmt = count_stmt.where(AssetDividend.asset_id == asset_id)

    if year:
        stmt       = stmt.where(func.extract("year", AssetDividend.ex_date) == year)
        count_stmt = count_stmt.where(func.extract("year", AssetDividend.ex_date) == year)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt  = (
        stmt
        .order_by(AssetDividend.ex_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    return result.scalars().all(), total


async def get_dividend_summary(
    db: AsyncSession,
    portfolio_id: int,
    year: Optional[int] = None,
) -> dict:
    """
    Retorna totais agrupados por dividend_type para a carteira.
    """
    stmt = (
        select(
            AssetDividend.dividend_type,
            func.sum(Dividend.total_value).label("total"),
        )
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .where(Dividend.portfolio_id == portfolio_id)
    )

    if year:
        stmt = stmt.where(func.extract("year", AssetDividend.ex_date) == year)

    stmt = stmt.group_by(AssetDividend.dividend_type)
    rows = (await db.execute(stmt)).fetchall()

    return {
        "by_type": {
            row.dividend_type: float(row.total or 0)
            for row in rows
        },
        "total": sum(float(row.total or 0) for row in rows),
        "year": year,
    }


async def update_dividend_status(
    db: AsyncSession,
    portfolio_id: int,
    dividend_id: int,
    status: DividendStatus,
) -> Optional[Dividend]:
    """Permite atualizar status manualmente (ex: marcar como RECEBIDO)."""
    result = await db.execute(
        select(Dividend).where(
            Dividend.id == dividend_id,
            Dividend.portfolio_id == portfolio_id,
        )
    )
    div = result.scalar_one_or_none()
    if div:
        div.status = status
        await db.commit()
        await db.refresh(div)
    return div
