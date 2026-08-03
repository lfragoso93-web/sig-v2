"""Backfill enriquecido de snapshots com fluxos, proventos e retorno TWR.

O motor de snapshots e deliberadamente DB-only: ele nunca consulta provedores
externos. A sincronizacao de mercado deve preencher ``asset_prices`` antes ou em
paralelo. Quando faltar cobertura, o snapshot usa o fallback patrimonial legado,
marca ``has_partial_prices`` e permite que a camada de sincronizacao trate a
lacuna sem bloquear a reconstrucao historica.

Os fluxos externos ainda sao inferidos a partir das compras e vendas porque o
SGI nao possui conta-caixa. Por isso ``return_is_estimated`` permanece verdadeiro.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import DEDICATED_PRICE_TYPES, NO_QUOTE_TYPES
from app.models.asset import AssetType
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import OperationType, Transaction
from app.services.portfolio_snapshot_service import _calc_totals
from app.services.canonical_dividend_aggregation_service import (
    group_received_entitlements_by_day,
)
from app.services.canonical_dividend_entitlement_reader import (
    load_portfolio_dividend_entitlements,
)
from app.services.price_history_service import get_prices_at_date_batch
from app.services.twr_service import (
    append_compounded_return_pct,
    calculate_daily_twr_pct,
)

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_MONEY = Decimal("0.01")
_TECHNICAL_EVENT_PREFIX = "Evento corporativo - troca de ticker"
_NON_MARKET_VALUATION_TYPES = NO_QUOTE_TYPES | DEDICATED_PRICE_TYPES


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def _operation_value_brl(tx: Transaction) -> tuple[Decimal, Decimal, Decimal]:
    """Retorna quantidade, preco e taxas em BRL."""
    fx_rate = _decimal(getattr(tx, "fx_rate", None) or 1)
    quantity = _decimal(tx.quantity)
    price = _decimal(tx.price) * fx_rate
    fees = _decimal(tx.fees) * fx_rate
    return quantity, price, fees


def _is_technical_transaction(tx: Transaction) -> bool:
    return str(getattr(tx, "notes", "") or "").startswith(_TECHNICAL_EVENT_PREFIX)


def _transaction_asset_type(tx: Transaction) -> AssetType:
    raw = getattr(getattr(tx, "asset_type", None), "value", getattr(tx, "asset_type", None))
    try:
        return AssetType(str(raw))
    except (ValueError, TypeError):
        logger.warning(
            "[snapshot_twr] asset_type invalido para %s: %s; usando ACAO",
            getattr(tx, "ticker", "?"),
            raw,
        )
        return AssetType.ACAO


def build_open_quote_requirements(
    transactions: Iterable[Transaction],
    target_date: date,
) -> list[tuple[str, AssetType]]:
    """Retorna apenas posicoes abertas dependentes de cotacao de mercado.

    Renda fixa, Tesouro e demais tipos dedicados nao entram nesta lista. Eles
    pertencem aos respectivos motores de valuation e nao devem gerar lacunas em
    ``asset_prices`` nem marcar o snapshot como parcial por falta de cotacao
    generica.
    """
    quantities: dict[str, Decimal] = defaultdict(lambda: _ZERO)
    asset_types: dict[str, AssetType] = {}

    for tx in transactions:
        if tx.date > target_date:
            break
        ticker = str(tx.ticker).upper().strip()
        asset_types[ticker] = _transaction_asset_type(tx)
        quantity = _decimal(tx.quantity)
        if tx.operation == OperationType.buy:
            quantities[ticker] += quantity
        elif tx.operation == OperationType.sell:
            quantities[ticker] -= quantity

    return [
        (ticker, asset_types[ticker])
        for ticker, quantity in quantities.items()
        if quantity > 0 and asset_types[ticker] not in _NON_MARKET_VALUATION_TYPES
    ]


def calculate_transaction_components(
    transactions: Iterable[Transaction],
    target_date: date,
) -> tuple[Decimal, Decimal]:
    """Calcula ganho realizado acumulado e fluxo externo liquido do dia."""
    states: dict[str, tuple[Decimal, Decimal]] = {}
    realized_pnl = _ZERO
    net_external_flow = _ZERO

    for tx in transactions:
        if tx.date > target_date:
            break

        ticker = str(tx.ticker).upper()
        quantity, price, fees = _operation_value_brl(tx)
        held_quantity, held_cost = states.get(ticker, (_ZERO, _ZERO))
        technical = _is_technical_transaction(tx)

        if tx.operation == OperationType.buy:
            held_quantity += quantity
            held_cost += quantity * price + fees
            if tx.date == target_date and not technical:
                net_external_flow += quantity * price + fees

        elif tx.operation == OperationType.sell:
            sold = min(quantity, held_quantity)
            average_cost = held_cost / held_quantity if held_quantity > 0 else _ZERO
            realized_pnl += sold * (price - average_cost) - fees
            held_quantity -= sold
            held_cost -= sold * average_cost
            held_quantity = max(held_quantity, _ZERO)
            held_cost = max(held_cost, _ZERO)
            if tx.date == target_date and not technical:
                net_external_flow -= quantity * price - fees

        states[ticker] = (held_quantity, held_cost)

    return realized_pnl.quantize(_MONEY), net_external_flow.quantize(_MONEY)


def _accumulated_dividends_at(
    accumulated_by_payment_date: dict[date, Decimal],
    target_date: date,
) -> Decimal:
    total = _ZERO
    for payment_date, value in accumulated_by_payment_date.items():
        if payment_date > target_date:
            break
        total = value
    return total


async def _has_partial_prices(
    db: AsyncSession,
    transactions: Iterable[Transaction],
    target_date: date,
) -> bool:
    requirements = build_open_quote_requirements(transactions, target_date)
    if not requirements:
        return False

    prices = await get_prices_at_date_batch(db, requirements, target_date.isoformat())
    missing = [ticker for ticker, _ in requirements if ticker not in prices]
    if missing:
        logger.warning(
            "[snapshot_twr] cobertura parcial portfolio_date=%s tickers=%s",
            target_date,
            ",".join(sorted(missing)),
        )
    return bool(missing)


async def _upsert_enriched_snapshot(
    db: AsyncSession,
    portfolio_id: int,
    snapshot_date: date,
    values: dict,
) -> None:
    stmt = (
        pg_insert(PortfolioSnapshot)
        .values(portfolio_id=portfolio_id, snapshot_date=snapshot_date, **values)
        .on_conflict_do_update(
            constraint="uq_snapshot_portfolio_date",
            set_=values,
        )
    )
    await db.execute(stmt)


async def backfill_snapshots_with_returns(
    db: AsyncSession,
    portfolio_id: int,
    days_back: int | None = None,
) -> int:
    """Reconstroi snapshots e TWR exclusivamente com dados persistidos."""
    tx_result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = list(tx_result.scalars().all())
    if not transactions:
        return 0

    dividends_day_map, dividends_accumulated_map = group_received_entitlements_by_day(
        await load_portfolio_dividend_entitlements(db, portfolio_id)
    )

    start = transactions[0].date
    if days_back is not None:
        start = max(start, date.today() - timedelta(days=days_back))

    previous_value = _ZERO
    accumulated_return = _ZERO
    count = 0
    cursor = start
    today = date.today()

    while cursor <= today:
        if cursor.weekday() < 5:
            totals = await _calc_totals(db, portfolio_id, cursor)
            realized_pnl, net_external_flow = calculate_transaction_components(
                transactions,
                cursor,
            )
            totals["realized_pnl"] = realized_pnl
            totals["total_pnl"] = (
                realized_pnl + _decimal(totals["unrealized_pnl"])
            ).quantize(_MONEY)

            dividends_day = dividends_day_map.get(cursor, _ZERO)
            dividends_accumulated = _accumulated_dividends_at(
                dividends_accumulated_map,
                cursor,
            )
            current_value = _decimal(totals["market_value"])
            daily_return = calculate_daily_twr_pct(
                previous_value,
                current_value,
                net_external_flow=net_external_flow,
                dividends_day=dividends_day,
            )
            accumulated_return = append_compounded_return_pct(
                accumulated_return,
                daily_return,
            )

            values = {
                **totals,
                "net_external_flow": net_external_flow,
                "dividends_day": dividends_day,
                "dividends_accumulated": dividends_accumulated,
                "daily_return_pct": daily_return,
                "accumulated_return_pct": accumulated_return,
                "has_partial_prices": await _has_partial_prices(
                    db,
                    transactions,
                    cursor,
                ),
                "return_is_estimated": True,
            }
            await _upsert_enriched_snapshot(db, portfolio_id, cursor, values)
            previous_value = current_value
            count += 1
            if count % 30 == 0:
                await db.commit()
        cursor += timedelta(days=1)

    await db.commit()
    logger.info(
        "[snapshot_twr] portfolio=%s snapshots=%s start=%s mode=db_only",
        portfolio_id,
        count,
        start,
    )
    return count
