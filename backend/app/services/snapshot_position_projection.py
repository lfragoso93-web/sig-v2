"""Adaptação read-only de transações de carteira para projeções históricas."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.models.transaction import OperationType, Transaction
from app.services.corporate_action_engine import NormalizedCorporateAction
from app.services.position_timeline_projection import (
    PositionMovement,
    PositionMovementKind,
    PositionTimelineProjection,
    project_position_timeline,
)
from app.services.corporate_action_multi_asset_timeline import (
    expand_component_bonus_movements,
)

_USD_ASSET_TYPES = {"STOCK", "ETF_INTERNACIONAL"}


def _asset_type_value(value: object) -> str:
    return str(getattr(value, "value", value) or "").upper()


def _movement_from_transaction(tx: Transaction) -> PositionMovement:
    asset_type = _asset_type_value(tx.asset_type)
    is_usd = (
        str(getattr(tx, "currency", "BRL") or "BRL").upper() == "USD"
        or asset_type in _USD_ASSET_TYPES
    )
    fx_rate = Decimal(1)
    saved_rate = getattr(tx, "fx_rate", None)
    if is_usd and saved_rate is not None and Decimal(str(saved_rate)) > 0:
        fx_rate = Decimal(str(saved_rate))

    price = Decimal(str(tx.price or 0))
    fees = Decimal(str(tx.fees or 0))
    kind = (
        PositionMovementKind.BUY
        if tx.operation == OperationType.buy
        else PositionMovementKind.SELL
    )
    return PositionMovement(
        movement_date=tx.date,
        kind=kind,
        quantity=Decimal(str(tx.quantity or 0)),
        unit_price=price * fx_rate,
        fees=fees * fx_rate,
        total_cost_original_currency=(
            Decimal(str(tx.quantity or 0)) * price + fees
            if is_usd and tx.operation == OperationType.buy
            else Decimal(0)
        ),
        transaction_id=getattr(tx, "id", None),
        ticker=str(tx.ticker).strip().upper(),
        asset_type=asset_type,
        currency=str(getattr(tx, "currency", "BRL") or "BRL").upper(),
        unit_price_original_currency=price if is_usd else None,
    )


def project_transaction_timelines(
    *,
    transactions: Iterable[Transaction],
    actions_by_ticker: Mapping[str, Sequence[NormalizedCorporateAction]],
    target_date: date,
) -> dict[str, tuple[PositionTimelineProjection, str, bool]]:
    """Projeta todas as linhas temporais, inclusive posições já encerradas."""

    transaction_list = list(transactions)
    movements_by_ticker: dict[str, list[PositionMovement]] = defaultdict(list)
    metadata: dict[str, tuple[str, bool]] = {}

    for tx in transaction_list:
        ticker = str(tx.ticker).strip().upper()
        asset_type = _asset_type_value(tx.asset_type)
        is_usd = (
            str(getattr(tx, "currency", "BRL") or "BRL").upper() == "USD"
            or asset_type in _USD_ASSET_TYPES
        )
        movements_by_ticker[ticker].append(_movement_from_transaction(tx))
        metadata[ticker] = (asset_type, is_usd)

    bonus_cash_rights = expand_component_bonus_movements(
        movements_by_ticker=movements_by_ticker,
        metadata_by_ticker=metadata,
        actions_by_ticker=actions_by_ticker,
        target_date=target_date,
    )

    projected: dict[str, tuple[PositionTimelineProjection, str, bool]] = {}
    for ticker, movements in movements_by_ticker.items():
        ticker_actions = tuple(
            action
            for action in actions_by_ticker.get(ticker, ())
            if action.component_bonus is None
        )
        result = project_position_timeline(
            movements=movements,
            actions=ticker_actions,
            through_date=target_date,
        )
        if ticker in bonus_cash_rights:
            result = replace(
                result,
                component_bonus_cash_rights=bonus_cash_rights[ticker],
            )
        asset_type, is_usd = metadata[ticker]
        projected[ticker] = (result, asset_type, is_usd)

    return projected


def project_snapshot_positions(
    *,
    transactions: Iterable[Transaction],
    actions_by_ticker: Mapping[str, Sequence[NormalizedCorporateAction]],
    target_date: date,
    include_pending_fractions: bool = False,
) -> dict[str, tuple[PositionTimelineProjection, str, bool]]:
    """Projeta posições abertas e, opcionalmente, pendências fracionárias."""

    projected = project_transaction_timelines(
        transactions=transactions,
        actions_by_ticker=actions_by_ticker,
        target_date=target_date,
    )
    return {
        ticker: item
        for ticker, item in projected.items()
        if item[0].quantity > 0
        or (
            include_pending_fractions
            and item[0].pending_corporate_action_fractions
        )
    }
