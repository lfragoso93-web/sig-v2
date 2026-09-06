"""CLI read-only para reconciliar a carteira sintética da Issue #303."""
from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.certification.portfolio_financial_reconciliation import (
    assert_declared_financial_expectations,
    calculate_independent_financial_reconciliation,
)
from app.certification.portfolio_seed_contract import load_synthetic_seed_identity
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)
from app.core.database import AsyncSessionLocal
from app.models.portfolio import Portfolio
from app.models.user import User, UserRole
from app.services.dividend_service import list_dividends
from app.services.portfolio_canonical_valuation_service import (
    calculate_canonical_portfolio_totals,
)
from app.services.portfolio_snapshot_service import _build_positions_at

_MONEY = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(_MONEY)


async def _load_portfolio_identity(db) -> tuple[int, int]:
    identity = load_synthetic_seed_identity()
    result = await db.execute(
        select(Portfolio.id, User.id)
        .join(User, User.id == Portfolio.user_id)
        .where(
            User.email == identity.user_email,
            User.name == identity.user_name,
            User.role == UserRole.user,
            User.is_active.is_(True),
            Portfolio.name == identity.portfolio_name,
            Portfolio.description == identity.ownership_marker,
            Portfolio.is_active.is_(True),
        )
    )
    rows = list(result.all())
    if len(rows) != 1:
        raise RuntimeError("synthetic certification portfolio identity is not unique")
    return int(rows[0][0]), int(rows[0][1])


async def main() -> None:
    fixture = load_portfolio_synthetic_certification_fixture()
    target_date = date.fromisoformat(fixture["market_prices"]["as_of"])
    expected = calculate_independent_financial_reconciliation()
    assert_declared_financial_expectations(fixture, expected)

    async with AsyncSessionLocal() as db:
        portfolio_id, user_id = await _load_portfolio_identity(db)
        positions = await _build_positions_at(db, portfolio_id, target_date)
        totals = await calculate_canonical_portfolio_totals(db, portfolio_id, target_date)
        dividends = await list_dividends(db, portfolio_id, user_id)

    failures: list[str] = []
    for ticker, expected_holding in expected.holdings.items():
        state = positions.get(ticker)
        if state is None:
            failures.append(f"{ticker}:missing-position")
            continue
        if Decimal(str(state.qty)) != expected_holding.quantity:
            failures.append(f"{ticker}:quantity")
        if _money(state.cost) != expected_holding.remaining_cost:
            failures.append(f"{ticker}:remaining-cost")
        if _money(state.realized_pnl) != expected_holding.realized_pnl:
            failures.append(f"{ticker}:realized-pnl")

    unexpected = sorted(set(positions) - set(expected.holdings))
    if unexpected:
        failures.append("unexpected-positions=" + ",".join(unexpected))

    comparisons = {
        "remaining_cost": (_money(totals["cost_basis"]), expected.remaining_cost),
        "market_value": (_money(totals["market_value"]), expected.market_value),
        "realized_pnl": (_money(totals["realized_pnl"]), expected.realized_pnl),
        "open_pnl": (_money(totals["unrealized_pnl"]), expected.open_pnl),
    }
    for name, (actual, wanted) in comparisons.items():
        if actual != wanted:
            failures.append(f"{name}:actual={actual}:expected={wanted}")

    income = sum((_money(item.total_received) for item in dividends), Decimal("0.00"))
    if income != expected.income:
        failures.append(f"income:actual={income}:expected={expected.income}")
    total_pnl_with_income = _money(totals["total_pnl"]) + income
    if total_pnl_with_income != expected.total_pnl:
        failures.append(
            f"total-pnl-with-income:actual={total_pnl_with_income}:expected={expected.total_pnl}"
        )

    print(
        "CERT303-RECONCILE",
        f"portfolio_id={portfolio_id}",
        f"date={target_date.isoformat()}",
        f"positions={len(positions)}",
        f"remaining_cost={_money(totals['cost_basis'])}",
        f"market_value={_money(totals['market_value'])}",
        f"realized_pnl={_money(totals['realized_pnl'])}",
        f"open_pnl={_money(totals['unrealized_pnl'])}",
        f"income={income}",
        f"total_pnl_with_income={total_pnl_with_income}",
        f"status={'PASS' if not failures else 'FAIL'}",
    )
    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    asyncio.run(main())