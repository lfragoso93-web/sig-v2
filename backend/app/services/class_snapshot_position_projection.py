from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.asset import AssetType
from app.models.transaction import Transaction
from app.services.corporate_action_engine import NormalizedCorporateAction
from app.services.snapshot_position_projection import project_snapshot_positions

_ZERO = Decimal(0)


@dataclass(frozen=True)
class ClassProjectedPosition:
    ticker: str
    asset_type: AssetType
    quantity: Decimal
    cost: Decimal
    realized_pnl: Decimal
    has_pending_fraction: bool = False
    corporate_action_cash_flow_total: Decimal = _ZERO


def project_class_positions_at(
    transactions: Iterable[Transaction],
    actions_by_ticker: Mapping[str, Sequence[NormalizedCorporateAction]],
    *,
    target_date: date,
) -> dict[str, ClassProjectedPosition]:
    transactions_list = [
        transaction
        for transaction in transactions
        if transaction.date <= target_date
    ]
    projected = project_snapshot_positions(
        transactions=transactions_list,
        actions_by_ticker={
            ticker: tuple(actions)
            for ticker, actions in actions_by_ticker.items()
        },
        target_date=target_date,
        include_pending_fractions=True,
        include_corporate_action_cash_flows=True,
    )

    positions: dict[str, ClassProjectedPosition] = {}
    for ticker, (position, raw_asset_type, _is_usd) in projected.items():
        try:
            asset_type = AssetType(str(raw_asset_type).upper())
        except (TypeError, ValueError):
            continue
        valued_quantity = position.quantity
        valued_cost = position.total_cost
        if (
            valued_quantity <= _ZERO
            and valued_cost <= _ZERO
            and position.realized_pnl == _ZERO
            and not position.pending_corporate_action_fractions
            and not position.corporate_action_cash_flows
        ):
            continue
        cash_flow_total = sum(
            (Decimal(str(cf.gross_amount_brl)) for cf in position.corporate_action_cash_flows),
            _ZERO,
        )
        positions[ticker] = ClassProjectedPosition(
            ticker=ticker,
            asset_type=asset_type,
            quantity=valued_quantity,
            cost=valued_cost,
            realized_pnl=position.realized_pnl,
            has_pending_fraction=bool(
                position.pending_corporate_action_fractions
            ),
            corporate_action_cash_flow_total=cash_flow_total,
        )
    return positions


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
