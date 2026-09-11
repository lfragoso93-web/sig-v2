from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SIMPLE_SERVICE = BACKEND_ROOT / "app" / "services" / "portfolio_snapshot_service.py"
CANONICAL_WRITER = (
    BACKEND_ROOT / "app" / "services" / "portfolio_snapshot_canonical_twr_service.py"
)


def test_simple_snapshot_service_is_invalidation_only() -> None:
    source = SIMPLE_SERVICE.read_text(encoding="utf-8")

    forbidden = (
        "pg_insert",
        "calc_snapshot_at_date",
        "backfill_snapshots(",
        "refresh_today_snapshot",
        "snapshot_backfill_needed",
        "backfill_missing_snapshots_for_active_portfolios",
        "_upsert_snapshot",
    )
    for token in forbidden:
        assert token not in source

    assert "async def invalidate_snapshots_from(" in source


def test_canonical_snapshot_writer_remains_the_materialization_boundary() -> None:
    source = CANONICAL_WRITER.read_text(encoding="utf-8")

    assert "async def backfill_canonical_snapshots_with_returns(" in source
    assert "_upsert_enriched_snapshot" in source
