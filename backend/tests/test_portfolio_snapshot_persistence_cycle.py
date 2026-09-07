from pathlib import Path


def test_placeholder_snapshot_persistence_cycle_contract_documented():
    service = Path("app/services/portfolio_snapshot_service.py").read_text(encoding="utf-8")
    assert "calc_snapshot_at_date" in service
    assert "invalidate_snapshots_from" in service
    assert "backfill_snapshots" in service
