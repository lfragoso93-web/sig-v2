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


def test_snapshot_cycle_uses_canonical_persistence_contracts():
    source = Path("app/cli/portfolio_snapshot_certification_cycle.py").read_text(
        encoding="utf-8"
    )

    for token in (
        "load_certification_portfolio_identity",
        "backfill_canonical_snapshots_with_returns",
        "invalidate_snapshots_from",
        "end_date=target_date",
        "commit=False",
        "await db.begin_nested()",
        "await savepoint.rollback()",
        "await db.refresh(tx)",
        "await db.commit()",
    ):
        assert token in source
    assert "calc_snapshot_at_date" not in source


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

    assert "prefetch" not in source
    assert "provider" not in source.lower()


def test_snapshot_replay_is_backed_by_unique_upsert_contract():
    components = Path("app/services/portfolio_snapshot_twr_components.py").read_text(
        encoding="utf-8"
    )
    model = Path("app/models/portfolio_snapshot.py").read_text(encoding="utf-8")

    assert 'constraint="uq_snapshot_portfolio_date"' in components
    assert 'name="uq_snapshot_portfolio_date"' in model
