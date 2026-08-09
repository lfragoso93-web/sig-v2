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
    assert "from sqlalchemy import or_, select" in source


def test_official_history_preserves_provider_hierarchy() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert '_OFFICIAL_SOURCE = "tesouro_transparente"' in source
    assert '_FALLBACK_SOURCE = "brapi_treasury"' in source
    assert "fetch_official_treasury_history" in source
    assert "fetch_treasury_history" in source
