from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_WRITER = (
    BACKEND_ROOT / "app" / "services" / "portfolio_snapshot_canonical_twr_service.py"
)


def test_snapshot_writer_delegates_to_canonical_valuation() -> None:
    source = CANONICAL_WRITER.read_text(encoding="utf-8")

    assert "calculate_canonical_portfolio_totals" in source
    assert "await calculate_canonical_portfolio_totals(" in source


def test_snapshot_writer_has_no_parallel_price_resolution_engine() -> None:
    source = CANONICAL_WRITER.read_text(encoding="utf-8")

    assert "get_persisted_prices_at_date_batch" not in source
    assert "resolve_missing_snapshot_prices" not in source
    assert "SnapshotPriceRequirement" not in source
