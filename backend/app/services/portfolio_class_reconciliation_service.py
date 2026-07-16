"""Reconciliação dos snapshots por classe com o snapshot consolidado."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import AssetType
from app.models.portfolio_class_snapshot import PortfolioClassSnapshot
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction
from app.services.portfolio_class_snapshot_service import SUPPORTED_CLASS_TWR_TYPES

_MONEY_TOLERANCE = Decimal("0.01")


def _decimal(value: object) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value or 0))


def _check(field: str, expected: object, observed: object) -> dict:
    expected_decimal = _decimal(expected)
    observed_decimal = _decimal(observed)
    difference = observed_decimal - expected_decimal
    return {
        "field": field,
        "expected": float(expected_decimal),
        "observed": float(observed_decimal),
        "difference": float(difference),
        "tolerance": float(_MONEY_TOLERANCE),
        "is_reconciled": abs(difference) <= _MONEY_TOLERANCE,
    }


async def reconcile_latest_class_snapshots(
    db: AsyncSession,
    portfolio_id: int,
) -> dict:
    type_result = await db.execute(
        select(Transaction.asset_type)
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
    )
    portfolio_types: set[AssetType] = set()
    unknown_types: set[str] = set()
    for value in type_result.scalars().all():
        raw = getattr(value, "value", value)
        try:
            portfolio_types.add(AssetType(str(raw).upper()))
        except (TypeError, ValueError):
            unknown_types.add(str(raw))

    unsupported = sorted(
        [item.value for item in portfolio_types if item not in SUPPORTED_CLASS_TWR_TYPES]
        + list(unknown_types)
    )
    if unsupported:
        return {
            "is_reconciled": None,
            "is_comparable": False,
            "status": "not_comparable_unsupported_classes",
            "unsupported_asset_types": unsupported,
            "snapshot_date": None,
            "checks": [],
        }

    snapshot_result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(1)
    )
    snapshot = snapshot_result.scalars().first()
    if snapshot is None:
        return {
            "is_reconciled": None,
            "is_comparable": False,
            "status": "missing_portfolio_snapshot",
            "unsupported_asset_types": [],
            "snapshot_date": None,
            "checks": [],
        }

    class_result = await db.execute(
        select(
            func.coalesce(func.sum(PortfolioClassSnapshot.market_value), 0),
            func.coalesce(func.sum(PortfolioClassSnapshot.cost_basis), 0),
            func.coalesce(func.sum(PortfolioClassSnapshot.net_external_flow), 0),
            func.coalesce(func.sum(PortfolioClassSnapshot.dividends_day), 0),
            func.count(PortfolioClassSnapshot.id),
        ).where(
            PortfolioClassSnapshot.portfolio_id == portfolio_id,
            PortfolioClassSnapshot.snapshot_date == snapshot.snapshot_date,
        )
    )
    market_value, cost_basis, external_flow, dividends_day, class_count = class_result.one()
    if int(class_count or 0) == 0:
        return {
            "is_reconciled": None,
            "is_comparable": False,
            "status": "missing_class_snapshots",
            "unsupported_asset_types": [],
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "checks": [],
        }

    checks = [
        _check("market_value", snapshot.market_value, market_value),
        _check("cost_basis", snapshot.cost_basis, cost_basis),
        _check("net_external_flow", snapshot.net_external_flow, external_flow),
        _check("dividends_day", snapshot.dividends_day, dividends_day),
    ]
    return {
        "is_reconciled": all(check["is_reconciled"] for check in checks),
        "is_comparable": True,
        "status": "evaluated",
        "unsupported_asset_types": [],
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "checks": checks,
    }
