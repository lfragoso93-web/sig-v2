"""CLI read-only para reconciliar a carteira sintética da Issue #303."""
from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

from app.certification.portfolio_financial_reconciliation import (
    calculate_independent_financial_reconciliation,
)
from app.certification.portfolio_seed_identity_service import (
    ensure_synthetic_portfolio_identity,
)
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)
from app.core.database import AsyncSessionLocal
from app.services.portfolio_canonical_valuation_service import (
    calculate_canonical_portfolio_totals,
)
from app.services.portfolio_snapshot_service import _build_positions_at

_MONEY = Decimal("0.01")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(_MONEY)


async def main() -> None:
    fixture = load_portfolio_synthetic_certification_fixture()
    target_date = date.fromisoformat(fixture["market_prices"]["as_of"])
    expected = calculate_independent_financial_reconciliation()

    async with AsyncSessionLocal() as db:
        identity = await ensure_synthetic_portfolio_identity(db)
        positions = await _build_positions_at(db, identity.portfolio_id, target_date)
        totals = await calculate_canonical_portfolio_totals(
            db,
            identity.portfolio_id,
            target_date,
        )

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

    print(
        "CERT303-RECONCILE",
        f"portfolio_id={identity.portfolio_id}",
        f"date={target_date.isoformat()}",
        f"positions={len(positions)}",
        f"remaining_cost={_money(totals['cost_basis'])}",
        f"market_value={_money(totals['market_value'])}",
        f"realized_pnl={_money(totals['realized_pnl'])}",
        f"open_pnl={_money(totals['unrealized_pnl'])}",
        f"income={expected.income}",
        f"total_pnl_with_income={expected.total_pnl}",
        f"status={'PASS' if not failures else 'FAIL'}",
    )
    if failures:
        raise RuntimeError("; ".join(failures))


if __name__ == "__main__":
    asyncio.run(main())
