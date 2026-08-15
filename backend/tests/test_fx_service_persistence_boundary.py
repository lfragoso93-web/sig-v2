from pathlib import Path


SOURCE = Path("app/services/fx_service.py")


def test_fx_service_is_persistence_only() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    assert "async def persist_usd_brl_rate" in source
    assert "ON CONFLICT (pair, rate_date)" in source
    assert "app.integrations" not in source
    assert "httpx" not in source
    assert "FALLBACK_RATE" not in source
    assert "async def get_usd_brl_" not in source
