from pathlib import Path
from types import SimpleNamespace

from app.cli.portfolio_snapshot_certification_cycle import _snapshot_signature


def test_snapshot_signature_accepts_mapping_and_orm_like_object():
    values = {
        "market_value": "38960.00",
        "cost_basis": "37629.30",
        "realized_pnl": "450.80",
        "unrealized_pnl": "1330.70",
        "total_pnl": "1781.50",
    }
    orm_like = SimpleNamespace(**values)

    expected = (
        values["market_value"],
        values["cost_basis"],
        values["realized_pnl"],
        values["unrealized_pnl"],
        values["total_pnl"],
    )
    assert tuple(str(item) for item in _snapshot_signature(values)) == expected
    assert tuple(str(item) for item in _snapshot_signature(orm_like)) == expected


def test_snapshot_cycle_uses_existing_persistence_contracts():
    source = Path("app/cli/portfolio_snapshot_certification_cycle.py").read_text(
        encoding="utf-8"
    )

    for token in (
        "load_certification_portfolio_identity",
        "calc_snapshot_at_date",
        "invalidate_snapshots_from",
        "await db.begin_nested()",
        "await savepoint.rollback()",
        "await db.refresh(tx)",
        "await db.commit()",
    ):
        assert token in source


def test_snapshot_cycle_mutation_is_exactly_scoped_to_cert303_petr4():
    source = Path("app/cli/portfolio_snapshot_certification_cycle.py").read_text(
        encoding="utf-8"
    )

    for token in (
        '_MUTATION_TICKER = "CERT303-PETR4"',
        "_MUTATION_DATE = date(2026, 1, 2)",
        '_MUTATION_QUANTITY = Decimal("100.00000000")',
        '_MUTATION_PRICE = Decimal("20.00000000")',
        '_MUTATION_FEES = Decimal("5.00")',
        '_MUTATION_FEE_DELTA = Decimal("1.00")',
        "synthetic mutation transaction identity is not unique",
    ):
        assert token in source


def test_snapshot_cycle_does_not_use_provider_prefetch():
    source = Path("app/cli/portfolio_snapshot_certification_cycle.py").read_text(
        encoding="utf-8"
    )

    assert "prefetch=False" in source
    assert "provider" not in source.lower()
