"""Write-capable local certification cycle for synthetic PortfolioSnapshot data."""
from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.certification.portfolio_certification_identity import (
    load_certification_portfolio_identity,
)
from app.certification.portfolio_financial_reconciliation import (
    assert_declared_financial_expectations,
    calculate_independent_financial_reconciliation,
)
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)
from app.core.database import AsyncSessionLocal
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import OperationType, Transaction
from app.services.portfolio_snapshot_service import (
    calc_snapshot_at_date,
    invalidate_snapshots_from,
)

_MONEY = Decimal("0.01")
_MUTATION_FEE_DELTA = Decimal("1.00")
_MUTATION_TICKER = "CERT303-PETR4"
_MUTATION_DATE = date(2026, 1, 2)
_MUTATION_QUANTITY = Decimal("100.00000000")
_MUTATION_PRICE = Decimal("20.00000000")
_MUTATION_FEES = Decimal("5.00")


def _money(value: object) -> Decimal:
    return Decimal(str(value)).quantize(_MONEY)


def _snapshot_signature(values: object) -> tuple[Decimal, ...]:
    return (
        _money(getattr(values, "market_value", values["market_value"])),
        _money(getattr(values, "cost_basis", values["cost_basis"])),
        _money(getattr(values, "realized_pnl", values["realized_pnl"])),
        _money(getattr(values, "unrealized_pnl", values["unrealized_pnl"])),
        _money(getattr(values, "total_pnl", values["total_pnl"])),
    )


def _expected_signature() -> tuple[Decimal, ...]:
    expected = calculate_independent_financial_reconciliation()
    price_only_total = expected.realized_pnl + expected.open_pnl
    return (
        expected.market_value,
        expected.remaining_cost,
        expected.realized_pnl,
        expected.open_pnl,
        price_only_total,
    )


async def _load_snapshot(db, portfolio_id: int, target_date: date) -> PortfolioSnapshot:
    result = await db.execute(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date == target_date,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise RuntimeError("certification snapshot was not persisted")
    return row


async def _snapshot_count(db, portfolio_id: int, target_date: date) -> int:
    result = await db.execute(
        select(func.count(PortfolioSnapshot.id)).where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date == target_date,
        )
    )
    return int(result.scalar_one() or 0)


async def _load_mutation_transaction(db, portfolio_id: int) -> Transaction:
    result = await db.execute(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == _MUTATION_TICKER,
            Transaction.operation == OperationType.buy,
            Transaction.date == _MUTATION_DATE,
            Transaction.quantity == _MUTATION_QUANTITY,
            Transaction.price == _MUTATION_PRICE,
            Transaction.fees == _MUTATION_FEES,
        )
    )
    rows = list(result.scalars().all())
    if len(rows) != 1:
        raise RuntimeError("synthetic mutation transaction identity is not unique")
    return rows[0]


async def main() -> None:
    fixture = load_portfolio_synthetic_certification_fixture()
    expected = calculate_independent_financial_reconciliation()
    assert_declared_financial_expectations(fixture, expected)
    target_date = date.fromisoformat(fixture["market_prices"]["as_of"])
    wanted = _expected_signature()

    async with AsyncSessionLocal() as db:
        portfolio_id, _ = await load_certification_portfolio_identity(db)

        baseline_totals = await calc_snapshot_at_date(
            db, portfolio_id, target_date, commit=True, prefetch=False
        )
        baseline_row = await _load_snapshot(db, portfolio_id, target_date)
        baseline = _snapshot_signature(baseline_row)
        if baseline != wanted or _snapshot_signature(baseline_totals) != wanted:
            raise RuntimeError(f"baseline snapshot mismatch: actual={baseline}:expected={wanted}")
        if await _snapshot_count(db, portfolio_id, target_date) != 1:
            raise RuntimeError("baseline snapshot uniqueness failed")

        replay_totals = await calc_snapshot_at_date(
            db, portfolio_id, target_date, commit=True, prefetch=False
        )
        replay_row = await _load_snapshot(db, portfolio_id, target_date)
        replay = _snapshot_signature(replay_row)
        if replay != baseline or _snapshot_signature(replay_totals) != baseline:
            raise RuntimeError("snapshot replay changed certified values")
        if await _snapshot_count(db, portfolio_id, target_date) != 1:
            raise RuntimeError("snapshot replay created a duplicate row")

        deleted = await invalidate_snapshots_from(
            db, portfolio_id, target_date, commit=True
        )
        if deleted != 1 or await _snapshot_count(db, portfolio_id, target_date) != 0:
            raise RuntimeError("snapshot invalidation did not remove exactly the target row")

        rebuilt_totals = await calc_snapshot_at_date(
            db, portfolio_id, target_date, commit=True, prefetch=False
        )
        rebuilt_row = await _load_snapshot(db, portfolio_id, target_date)
        rebuilt = _snapshot_signature(rebuilt_row)
        if rebuilt != baseline or _snapshot_signature(rebuilt_totals) != baseline:
            raise RuntimeError("snapshot rebuild did not restore certified values")
        if await _snapshot_count(db, portfolio_id, target_date) != 1:
            raise RuntimeError("snapshot rebuild uniqueness failed")

        tx = await _load_mutation_transaction(db, portfolio_id)
        original_fees = Decimal(str(tx.fees))
        savepoint = await db.begin_nested()
        try:
            tx.fees = original_fees + _MUTATION_FEE_DELTA
            await db.flush()
            await invalidate_snapshots_from(db, portfolio_id, target_date, commit=False)
            mutated_totals = await calc_snapshot_at_date(
                db, portfolio_id, target_date, commit=False, prefetch=False
            )
            mutated_row = await _load_snapshot(db, portfolio_id, target_date)
            mutated = _snapshot_signature(mutated_row)
            if mutated == baseline or _snapshot_signature(mutated_totals) == baseline:
                raise RuntimeError("synthetic mutation did not change the snapshot")
            if mutated[4] != baseline[4] - _MUTATION_FEE_DELTA:
                raise RuntimeError(
                    f"synthetic mutation total_pnl drift is unexpected: {mutated[4]}"
                )
        finally:
            await savepoint.rollback()

        await db.refresh(tx)
        if Decimal(str(tx.fees)) != original_fees:
            raise RuntimeError("synthetic transaction mutation escaped savepoint rollback")

        await invalidate_snapshots_from(db, portfolio_id, target_date, commit=False)
        restored_totals = await calc_snapshot_at_date(
            db, portfolio_id, target_date, commit=False, prefetch=False
        )
        await db.commit()

        restored_row = await _load_snapshot(db, portfolio_id, target_date)
        restored = _snapshot_signature(restored_row)
        if restored != baseline or _snapshot_signature(restored_totals) != baseline:
            raise RuntimeError("final snapshot did not return to certified baseline")
        if await _snapshot_count(db, portfolio_id, target_date) != 1:
            raise RuntimeError("final snapshot uniqueness failed")

        tx = await _load_mutation_transaction(db, portfolio_id)
        if Decimal(str(tx.fees)) != original_fees:
            raise RuntimeError("final synthetic transaction state is not restored")

    print(
        "CERT303-SNAPSHOT-CYCLE",
        f"portfolio_id={portfolio_id}",
        f"date={target_date.isoformat()}",
        f"market_value={baseline[0]}",
        f"cost_basis={baseline[1]}",
        f"realized_pnl={baseline[2]}",
        f"unrealized_pnl={baseline[3]}",
        f"total_pnl={baseline[4]}",
        "replay_rows=1",
        f"invalidated={deleted}",
        f"mutated_total_pnl={mutated[4]}",
        f"restored_total_pnl={restored[4]}",
        "status=PASS",
    )


if __name__ == "__main__":
    asyncio.run(main())
