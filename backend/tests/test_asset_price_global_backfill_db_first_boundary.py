from pathlib import Path


SERVICE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "asset_price_global_backfill_service.py"
)


def _source() -> str:
    return SERVICE_PATH.read_text(encoding="utf-8")


def test_global_backfill_does_not_create_catalog_assets() -> None:
    source = _source()

    assert "ensure_transaction_assets_in_catalog" not in source
    assert "db.add(" not in source
    assert "Transaction" not in source
    assert "catalog_created" not in source


def test_global_backfill_reports_missing_assets_without_syncing_them() -> None:
    source = _source()

    assert "missing_assets = [item for item in coverage if item.asset_id is None]" in source
    assert "item.needs_sync and item.asset_id is not None" in source
    assert '"missing_assets": len(missing_assets)' in source
