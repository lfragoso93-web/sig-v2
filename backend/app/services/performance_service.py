"""
performance_service.py

Calcula rentabilidade por ativo para um portfolio.

Cache Redis (TTL 5 min, chave `perf:{portfolio_id}`):
- Se Redis indisponivel, calcula direto sem cache (degradacao gracosa).
- Cache e invalidado automaticamente por TTL — nao ha invalidacao explicita
  pois este servico e usado apenas no router /performance, chamado raramente.
"""
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.transaction import Transaction
from app.models.asset import Asset
from app.services.quotes_service import get_current_price
from app.core.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # 5 minutos
_CACHE_PREFIX = "perf"


def _cache_key(portfolio_id: int) -> str:
    return f"{_CACHE_PREFIX}:{portfolio_id}"


async def get_portfolio_performance(
    db: AsyncSession, portfolio_id: int, user_id: int
) -> dict:
    """
    Retorna metricas de rentabilidade do portfolio.
    Tenta cache Redis (TTL 5min) antes de calcular.
    """
    key = _cache_key(portfolio_id)

    # --- Tenta cache ---
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
        p = positions[ticker]
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        op = (tx.operation or "").lower()
        if op in ("buy", "compra"):
            p["quantity"] += qty
            p["invested"] += qty * price + float(tx.fees or 0)
        elif op in ("sell", "venda"):
            p["quantity"] -= qty
            p["invested"] -= qty * price

    items = []
    for ticker, p in positions.items():
        if p["quantity"] <= 0:
            continue

        asset_type_str = (
            p["asset_type"] if isinstance(p["asset_type"], str)
            else str(p["asset_type"].value)
        )
        current_price = await get_current_price(ticker, asset_type=asset_type_str, db=db)

        if current_price:
            p["current_value"] = p["quantity"] * current_price
        else:
            avg_price = p["invested"] / p["quantity"] if p["quantity"] else 0
            p["current_value"] = p["quantity"] * avg_price
            logger.warning(
                "[performance] cotacao indisponivel para %s, usando preco medio", ticker
            )

        gain = p["current_value"] - p["invested"]
        gain_pct = (gain / p["invested"] * 100) if p["invested"] else 0.0

        asset_result = await db.execute(select(Asset).where(Asset.ticker == ticker))
        asset = asset_result.scalar_one_or_none()

        items.append({
            "ticker": ticker,
            "name": asset.name if asset else ticker,
            "asset_type": asset_type_str,
            "quantity": round(p["quantity"], 8),
            "invested": round(p["invested"], 2),
            "current_value": round(p["current_value"], 2),
            "gain": round(gain, 2),
            "gain_pct": round(gain_pct, 4),
        })

    total_invested = round(sum(i["invested"] for i in items), 2)
    total_current = round(sum(i["current_value"] for i in items), 2)
    total_gain = round(total_current - total_invested, 2)
    total_gain_pct = round(
        (total_gain / total_invested * 100) if total_invested else 0.0, 4
    )

    payload = {
        "total_invested": total_invested,
        "total_current_value": total_current,
        "total_gain": total_gain,
        "total_gain_pct": total_gain_pct,
        "positions": items,
    }

    # --- Salva no cache ---
    await cache_set(key, payload, ttl=_CACHE_TTL)
    logger.debug("[performance] cache set portfolio=%s TTL=%ss", portfolio_id, _CACHE_TTL)

    return payload
