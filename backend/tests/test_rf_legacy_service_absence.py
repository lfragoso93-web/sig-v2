from pathlib import Path


APP = Path("app")
LEGACY_SERVICE = APP / "services" / "rf_calc_service.py"


def test_legacy_rf_provider_service_is_absent() -> None:
    assert not LEGACY_SERVICE.exists()

    consumers = "\n".join(
        path.read_text(encoding="utf-8")
        for path in APP.rglob("*.py")
        if path != LEGACY_SERVICE
    )
    assert "rf_calc_service" not in consumers
    assert "enrich_rf_positions" not in consumers
