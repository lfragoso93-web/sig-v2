"""
performance_service.py

Monta a visao de rentabilidade por ativo para um portfolio.

Os totais consolidados sao obtidos de portfolio_summary_service, garantindo a
mesma fonte de verdade usada por Resumo e Patrimonio. A lista detalhada de
posicoes permanece neste servico por compatibilidade com o endpoint legado.
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.models.asset import Asset
from app.models.transaction import Transaction
from app.services.portfolio_summary_service import get_canonical_portfolio_summary
from app.services.quotes_service import get_current_price

logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # 5 minutos
# v2 evita reutilizar payloads calculados antes da consolidacao dos KPIs.
_CACHE_PREFIX = "perf:v2"


def _cache_key(portfolio_id: int) -> str:
    return f"{_CACHE_PREFIX}:{portfolio_id}"


async def get_portfolio_performance(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> dict:
    """Retorna posicoes legadas com totais vindos do resumo canonico."""
    key = _cache_key(portfolio_id)

    cached = await cache_get(key)
    if cached:
        logger.debug("[performance] cache hit portfolio=%s", portfolio_id)
        return cached

    logger.debug("[performance] cache miss portfolio=%s — calculando", portfolio_id)

    result = await db.execute(
        select(Transaction).where(Transaction.portfolio_id == portfolio_id)
    )
    transactions = result.scalars().all()

    positions: dict[str, dict] = {}
    for tx in transactions:
        ticker = tx.ticker
        if ticker not in positions:
            positions[ticker] = {
                "ticker": ticker,
                "asset_type": tx.asset_type,
                "quantity": 0.0,
                "invested": 0.0,
                "current_value": 0.0,
            }

        position = positions[ticker]
        quantity = float(tx.quantity or 0)
        price = float(tx.price or 0)
        operation = (tx.operation or "").lower()

        if operation in ("buy", "compra"):
            position["quantity"] += quantity
            position["invested"] += quantity * price + float(tx.fees or 0)
        elif operation in ("sell", "venda"):
            position["quantity"] -= quantity
            position["invested"] -= quantity * price

    items = []
    for ticker, position in positions.items():
        if position["quantity"] <= 0:
            continue

        asset_type_str = (
            position["asset_type"]
            if isinstance(position["asset_type"], str)
            else str(position["asset_type"].value)
        )
        current_price = await get_current_price(
            ticker,
            asset_type=asset_type_str,
            db=db,
        )

        if current_price:
            position["current_value"] = position["quantity"] * current_price
        else:
            average_price = (
                position["invested"] / position["quantity"]
                if position["quantity"]
                else 0
            )
            position["current_value"] = position["quantity"] * average_price
            logger.warning(
                "[performance] cotacao indisponivel para %s, usando preco medio",
                ticker,
            )

        gain = position["current_value"] - position["invested"]
        gain_pct = (
            gain / position["invested"] * 100
            if position["invested"]
            else 0.0
        )

        asset_result = await db.execute(
            select(Asset).where(Asset.ticker == ticker)
        )
        asset = asset_result.scalar_one_or_none()

        items.append({
            "ticker": ticker,
            "name": asset.name if asset else ticker,
            "asset_type": asset_type_str,
            "quantity": round(position["quantity"], 8),
            "invested": round(position["invested"], 2),
            "current_value": round(position["current_value"], 2),
            "gain": round(gain, 2),
            "gain_pct": round(gain_pct, 4),
        })

    summary = await get_canonical_portfolio_summary(
        db,
        portfolio_id,
        user_id,
    )

    payload = {
        "total_invested": summary["total_invested"],
        "total_current_value": summary["current_value"],
        "total_gain": summary["total_gain"],
        "total_gain_pct": summary["total_gain_pct"],
        "positions": items,
    }

    await cache_set(key, payload, ttl=_CACHE_TTL)
    logger.debug("[performance] cache set portfolio=%s TTL=%ss", portfolio_id, _CACHE_TTL)
    return payload
