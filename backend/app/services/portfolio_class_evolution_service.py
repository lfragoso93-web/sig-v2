"""Historico patrimonial mensal filtrado por classe de ativo.

A serie por classe e derivada exclusivamente de transacoes e precos historicos
persistidos no banco. Nao consulta provedores externos durante a leitura.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, OperationType
from app.services.price_history_service import get_price_at_date

logger = logging.getLogger(__name__)


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    return date(year, month + 1, 1) - timedelta(days=1)


def _parse_asset_type(asset_type: str) -> AssetType | None:
    try:
        return AssetType(asset_type.upper())
    except ValueError:
        logger.warning("[class_evo] asset_type desconhecido: %s", asset_type)
        return None


async def _history_start(
    db: AsyncSession,
    portfolio_id: int,
    parsed_type: AssetType,
    months: int,
) -> date | None:
    if months > 0:
        return date.today() - timedelta(days=months * 31)
    result = await db.execute(
        select(func.min(Transaction.date)).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_type == parsed_type,
        )
    )
    return result.scalar_one_or_none()


async def get_monthly_evolution_by_class(
    db: AsyncSession,
    portfolio_id: int,
    months: int = 12,
    asset_type: str = "",
) -> list[dict]:
    """Retorna fechamento mensal da classe; ``months <= 0`` usa todo o periodo."""
    today = date.today()
    parsed_type = _parse_asset_type(asset_type)
    if parsed_type is None:
        return []

    since = await _history_start(db, portfolio_id, parsed_type, months)
    if since is None:
        return []

    result = await db.execute(
        select(Transaction.ticker)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.asset_type == parsed_type,
        )
        .distinct()
    )
    tickers = [str(row.ticker).upper() for row in result.all() if row.ticker]
    if not tickers:
        return []

    tx_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker.in_(tickers),
        )
        .order_by(Transaction.ticker, Transaction.date.asc(), Transaction.id.asc())
    )
    transactions_by_ticker: dict[str, list[Transaction]] = {ticker: [] for ticker in tickers}
    for transaction in tx_result.scalars().all():
        transactions_by_ticker.setdefault(str(transaction.ticker).upper(), []).append(transaction)

    asset_result = await db.execute(select(Asset).where(Asset.ticker.in_(tickers)))
    assets = {str(asset.ticker).upper(): asset for asset in asset_result.scalars().all()}

    months_to_process: list[tuple[int, int]] = []
    cursor = date(since.year, since.month, 1)
    while cursor <= today:
        months_to_process.append((cursor.year, cursor.month))
        cursor = date(cursor.year + (1 if cursor.month == 12 else 0), 1 if cursor.month == 12 else cursor.month + 1, 1)

    evolution: list[dict] = []
    for year, month in months_to_process:
        target = min(_month_end(year, month), today)
        market_value = Decimal("0")
        cost_basis = Decimal("0")
        has_partial_prices = False

        for ticker in tickers:
            quantity = Decimal("0")
            cost = Decimal("0")
            for transaction in transactions_by_ticker.get(ticker, []):
                if transaction.date > target:
                    break
                tx_quantity = Decimal(str(transaction.quantity or 0))
                tx_price = Decimal(str(transaction.price or 0))
                tx_fees = Decimal(str(transaction.fees or 0))
                if transaction.operation == OperationType.buy:
                    quantity += tx_quantity
                    cost += tx_quantity * tx_price + tx_fees
                elif transaction.operation == OperationType.sell:
                    sold = min(tx_quantity, quantity)
                    if quantity > 0:
                        average_cost = cost / quantity
                        cost -= sold * average_cost
                    quantity = max(quantity - sold, Decimal("0"))
                    cost = max(cost, Decimal("0"))

            if quantity <= 0:
                continue

            asset = assets.get(ticker)
            quote_type = parsed_type if asset is None else asset.asset_type
            close = await get_price_at_date(db, ticker, quote_type, target.isoformat())
            if close is None:
                has_partial_prices = True
                close = float(cost / quantity if quantity > 0 else Decimal("0"))
                logger.warning("[class_evo] sem cotacao %s em %s; usando custo medio", ticker, target)

            market_value += quantity * Decimal(str(close))
            cost_basis += cost

        if market_value > 0 or cost_basis > 0:
            market_value = market_value.quantize(Decimal("0.01"))
            cost_basis = cost_basis.quantize(Decimal("0.01"))
            evolution.append(
                {
                    "date": target.isoformat(),
                    "period": target.strftime("%Y-%m"),
                    "value": float(market_value),
                    "invested": float(cost_basis),
                    "capital_result": float((market_value - cost_basis).quantize(Decimal("0.01"))),
                    "has_partial_prices": has_partial_prices,
                    "history_source": "db_derived_class_history",
                }
            )

    return evolution
