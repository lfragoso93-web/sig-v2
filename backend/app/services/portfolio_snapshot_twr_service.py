"""Backfill enriquecido de snapshots com fluxos, proventos e retorno TWR.

Este módulo mantém o cálculo patrimonial legado isolado e acrescenta a camada de
performance necessária para reconstruções históricas. Os fluxos externos ainda
são inferidos a partir das compras e vendas porque o SGI não possui conta-caixa.
Por isso ``return_is_estimated`` permanece verdadeiro.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.dividend import Dividend, DividendStatus
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import OperationType, Transaction
from app.services.portfolio_snapshot_service import (
    _calc_totals,
    _prefetch_price_history,
)
from app.services.twr_service import (
    append_compounded_return_pct,
    calculate_daily_twr_pct,
)

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_MONEY = Decimal("0.01")
_TECHNICAL_EVENT_PREFIX = "Evento corporativo - troca de ticker"
_NON_CASH_DIVIDEND_TYPES = {"BONIFICACAO", "SUBSCRICAO"}


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def _operation_value_brl(tx: Transaction) -> tuple[Decimal, Decimal, Decimal]:
    """Retorna quantidade, preço e taxas em BRL."""
    fx_rate = _decimal(getattr(tx, "fx_rate", None) or 1)
    quantity = _decimal(tx.quantity)
    price = _decimal(tx.price) * fx_rate
    fees = _decimal(tx.fees) * fx_rate
    return quantity, price, fees


def _is_technical_transaction(tx: Transaction) -> bool:
    return str(getattr(tx, "notes", "") or "").startswith(_TECHNICAL_EVENT_PREFIX)


def calculate_transaction_components(
    transactions: Iterable[Transaction],
    target_date: date,
) -> tuple[Decimal, Decimal]:
    """Calcula ganho realizado acumulado e fluxo externo líquido do dia.

    Compras são tratadas como aportes e vendas como retiradas porque ainda não
    existe saldo de caixa explícito. Taxas de compra integram o aporte; taxas de
    venda reduzem tanto o valor retirado quanto o ganho realizado.
    """
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


def _dividend_value(dividend: Dividend) -> Decimal:
    for field in ("net_value", "total_received", "total_value"):
        value = getattr(dividend, field, None)
        if value is not None:
            return _decimal(value)
    return _ZERO


def build_dividend_totals(
    dividends: Iterable[Dividend],
) -> tuple[dict[date, Decimal], dict[date, Decimal]]:
    """Indexa proventos monetários por data de pagamento e acumulado."""
    by_day: dict[date, Decimal] = defaultdict(lambda: _ZERO)

    for dividend in dividends:
        status = getattr(dividend.status, "value", dividend.status)
        if str(status).upper() != DividendStatus.RECEBIDO.value:
            continue
        dividend_type = str(dividend.dividend_type or "").upper()
        if dividend_type in _NON_CASH_DIVIDEND_TYPES:
            continue
        payment_date = dividend.payment_date or dividend.date_pagamento
        if payment_date is None:
            continue
        by_day[payment_date] += _dividend_value(dividend)

    accumulated: dict[date, Decimal] = {}
    running = _ZERO
    for payment_date in sorted(by_day):
        by_day[payment_date] = by_day[payment_date].quantize(_MONEY)
        running += by_day[payment_date]
        accumulated[payment_date] = running.quantize(_MONEY)
    return dict(by_day), accumulated


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
    portfolio_id: int,
    target_date: date,
) -> bool:
    """Detecta posições abertas sem cotação registrada exatamente na data."""
    tx_result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= target_date,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    quantities: dict[str, Decimal] = defaultdict(lambda: _ZERO)
    for tx in tx_result.scalars().all():
        quantity = _decimal(tx.quantity)
        if tx.operation == OperationType.buy:
            quantities[str(tx.ticker).upper()] += quantity
        elif tx.operation == OperationType.sell:
            quantities[str(tx.ticker).upper()] -= quantity

    open_tickers = [ticker for ticker, quantity in quantities.items() if quantity > 0]
    if not open_tickers:
        return False

    start = datetime.combine(target_date, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    result = await db.execute(
        select(func.count(func.distinct(Asset.ticker)))
        .select_from(Asset)
        .join(AssetPrice, AssetPrice.asset_id == Asset.id)
        .where(
            Asset.ticker.in_(open_tickers),
            AssetPrice.timestamp >= start,
            AssetPrice.timestamp < end,
        )
    )
    exact_prices = int(result.scalar_one() or 0)
    return exact_prices < len(set(open_tickers))


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
    """Reconstrói snapshots úteis e recalcula toda a cadeia TWR do período."""
    tx_result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = list(tx_result.scalars().all())
    if not transactions:
        return 0

    dividend_result = await db.execute(
        select(Dividend)
        .where(Dividend.portfolio_id == portfolio_id)
        .order_by(
            func.coalesce(Dividend.payment_date, Dividend.date_pagamento).asc(),
            Dividend.id.asc(),
        )
    )
    dividends_day_map, dividends_accumulated_map = build_dividend_totals(
        dividend_result.scalars().all()
    )

    start = transactions[0].date
    if days_back is not None:
        start = max(start, date.today() - timedelta(days=days_back))

    total_days = (date.today() - start).days + 1
    await _prefetch_price_history(db, portfolio_id, days_back=total_days)

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
                    portfolio_id,
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
        "[snapshot_twr] portfolio=%s snapshots=%s start=%s",
        portfolio_id,
        count,
        start,
    )
    return count
