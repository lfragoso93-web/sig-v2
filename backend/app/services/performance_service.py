"""
performance_service.py

Monta a visao de rentabilidade por ativo para um portfolio.

Os totais consolidados sao obtidos de portfolio_summary_service, garantindo a
mesma fonte de verdade usada por Resumo e Patrimonio. A lista detalhada de
posicoes permanece neste servico por compatibilidade com o endpoint legado.

Este servico nao mantem cache proprio: o resumo canonico ja possui cache curto e
invalidacao centralizada. Evitar uma segunda camada impede totais divergentes
apos novos lancamentos.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.services.portfolio_service import calc_raw_positions
from app.services.portfolio_summary_service import get_canonical_portfolio_summary
from app.services.quotes_service import get_current_price

logger = logging.getLogger(__name__)


async def get_portfolio_performance(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    """Retorna posicoes legadas com totais vindos do resumo canonico."""
    positions = await calc_raw_positions(db, portfolio_id)

    items = []
    for position in positions:
        ticker = str(position["ticker"]).upper()
        quantity = float(position.get("quantity") or 0)
        if quantity <= 0:
            continue

        asset_type = position.get("asset_type")
        asset_type_str = (
            asset_type if isinstance(asset_type, str) else str(asset_type.value)
        )
        invested = float(position.get("total_invested") or 0)
        current_price = await get_current_price(
            ticker,
            asset_type=asset_type_str,
            db=db,
        )

        if current_price:
            current_value = quantity * current_price
        else:
            average_price = invested / quantity if quantity else 0
            current_value = quantity * average_price
            logger.warning(
                "[performance] cotacao indisponivel para %s, usando preco medio",
                ticker,
            )

        gain = current_value - invested
        gain_pct = gain / invested * 100 if invested else 0.0

        asset_result = await db.execute(select(Asset).where(Asset.ticker == ticker))
        asset = asset_result.scalar_one_or_none()

        items.append(
            {
                "ticker": ticker,
                "name": asset.name if asset else ticker,
                "asset_type": asset_type_str,
                "quantity": round(quantity, 8),
                "invested": round(invested, 2),
                "current_value": round(current_value, 2),
                "gain": round(gain, 2),
                "gain_pct": round(gain_pct, 4),
            }
        )

    summary = await get_canonical_portfolio_summary(
        db,
        portfolio_id,
        user_id,
    )

    return {
        "total_invested": summary["total_invested"],
        "total_current_value": summary["current_value"],
        "total_gain": summary["total_gain"],
        "total_gain_pct": summary["total_gain_pct"],
        "positions": items,
    }
