from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from app.models.asset import AssetType
from app.models.transaction import Transaction
from app.services.corporate_action_position_reader import CorporateActionPosition
from app.services.snapshot_position_projection import project_snapshot_positions

_ZERO = Decimal("0")


@dataclass(frozen=True)
class ClassProjectedPosition:
    ticker: str
    asset_type: AssetType
    quantity: Decimal
    cost: Decimal
    realized_pnl: Decimal


def project_class_positions_at(
    transactions: Iterable[Transaction],
    actions_by_ticker: Mapping[str, Sequence[CorporateActionPosition]],
    *,
    target_date: date,
) -> dict[str, ClassProjectedPosition]:
    transactions_list = [
        transaction
        for transaction in transactions
        if transaction.date <= target_date
    ]
    projected = project_snapshot_positions(
        transactions_list,
        actions_by_ticker,
        target_date=target_date,
    )

    asset_types: dict[str, AssetType] = {}
    for transaction in transactions_list:
        ticker = str(transaction.ticker).upper()
        raw = getattr(transaction.asset_type, "value", transaction.asset_type)
        try:
            asset_types[ticker] = AssetType(str(raw).upper())
        except (TypeError, ValueError):
            continue

    return {
        ticker: ClassProjectedPosition(
            ticker=ticker,
            asset_type=asset_types[ticker],
            quantity=position.quantity,
            cost=position.cost_brl,
            realized_pnl=position.realized_pnl,
        )
        for ticker, position in projected.items()
        if ticker in asset_types
        and (
            position.quantity > _ZERO
            or position.cost_brl > _ZERO
            or position.realized_pnl != _ZERO
        )
    }


def aggregate_class_positions(
    positions: Iterable[ClassProjectedPosition],
) -> tuple[
    dict[AssetType, list[ClassProjectedPosition]],
    dict[AssetType, Decimal],
]:
    open_by_class: dict[AssetType, list[ClassProjectedPosition]] = defaultdict(list)
    realized_by_class: dict[AssetType, Decimal] = defaultdict(lambda: _ZERO)

    for position in positions:
        realized_by_class[position.asset_type] += position.realized_pnl
        if position.quantity > _ZERO:
            open_by_class[position.asset_type].append(position)

    return dict(open_by_class), dict(realized_by_class)
