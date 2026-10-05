"""Componentes compartilhados do snapshot TWR consolidado.

Este módulo contém apenas regras auxiliares reutilizadas pela fronteira canônica
de snapshots e pela checagem silenciosa de cobertura. Ele não executa backfill
nem representa um writer alternativo de ``PortfolioSnapshot``.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Iterable

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import DEDICATED_PRICE_TYPES, NO_QUOTE_TYPES
from app.models.asset import AssetType
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import OperationType, Transaction

logger = logging.getLogger(__name__)

_ZERO = Decimal("0")
_MONEY = Decimal("0.01")
_TECHNICAL_EVENT_PREFIX = "Evento corporativo - troca de ticker"
_NON_MARKET_VALUATION_TYPES = NO_QUOTE_TYPES | DEDICATED_PRICE_TYPES


def decimal_value(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def _operation_value_brl(tx: Transaction) -> tuple[Decimal, Decimal, Decimal]:
    fx_rate = decimal_value(getattr(tx, "fx_rate", None) or 1)
    quantity = decimal_value(tx.quantity)
    price = decimal_value(tx.price) * fx_rate
    fees = decimal_value(tx.fees) * fx_rate
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
    """Retorna apenas posições abertas que dependem de cotação de mercado."""
    quantities: dict[str, Decimal] = defaultdict(lambda: _ZERO)
    asset_types: dict[str, AssetType] = {}

    for tx in transactions:
        if tx.date > target_date:
            break
        ticker = str(tx.ticker).upper().strip()
        asset_types[ticker] = _transaction_asset_type(tx)
        quantity = decimal_value(tx.quantity)
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
    """Calcula ganho realizado acumulado e fluxo externo líquido do dia."""
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


def accumulated_dividends_at(
    accumulated_by_payment_date: dict[date, Decimal],
    target_date: date,
) -> Decimal:
    total = _ZERO
    for payment_date, value in accumulated_by_payment_date.items():
        if payment_date > target_date:
            break
        total = value
    return total


async def upsert_enriched_snapshot(
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
