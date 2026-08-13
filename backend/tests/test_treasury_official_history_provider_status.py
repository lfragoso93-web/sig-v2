from pathlib import Path


SERVICE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "treasury_official_history_service.py"
)


def test_official_history_keeps_nullable_provider_status() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "Asset.provider_status.is_(None)" in source
    assert "Asset.provider_status != _INACTIVE_STATUS" in source
    assert "from sqlalchemy import func, or_, select" in source


def test_official_history_preserves_provider_hierarchy() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert '_OFFICIAL_SOURCE = "tesouro_transparente"' in source
    assert '_FALLBACK_SOURCE = "brapi_treasury"' in source
    assert "fetch_official_treasury_history" in source
    assert "fetch_treasury_history" in source


def test_official_history_initial_backfill_starts_at_dataset_origin() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "_OFFICIAL_HISTORY_START = date(2002, 1, 1)" in source
    assert "_first_official_saved_date" in source
    assert "first_official_date is None" in source
    assert "start = _OFFICIAL_HISTORY_START" in source
    assert "_DEFAULT_YEARS" not in source


def test_official_history_skips_completed_matured_windows() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "_full_maturity_date_from_symbol" in source
    assert "historical_complete_symbols" in source
    assert "full_maturity < start" in source
    assert '"historical_complete_skipped"' in source
