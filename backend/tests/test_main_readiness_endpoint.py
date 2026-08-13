from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parents[1] / "app" / "main.py"


def _source() -> str:
    return MAIN_PATH.read_text(encoding="utf-8")


def test_main_exposes_separate_health_and_readiness_endpoints() -> None:
    source = _source()

    assert '@app.get("/health"' in source
    assert '@app.get("/ready"' in source
    assert "ready_for_real_data" in source
    assert "get_bootstrap_readiness" in source


def test_health_does_not_claim_operational_readiness() -> None:
    source = _source()

    health_block = source.split('@app.get("/health"', 1)[1].split('@app.get("/ready"', 1)[0]
    assert '"bootstrap": get_bootstrap_readiness().to_dict()' in health_block
    assert "ready_for_real_data else 503" not in health_block
