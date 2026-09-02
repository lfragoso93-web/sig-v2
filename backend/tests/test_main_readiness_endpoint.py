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

    health_block = source.split('@app.get("/health"', 1)[1].split(
        '@app.get("/ready"',
        1,
    )[0]
    assert '"bootstrap": get_bootstrap_readiness().to_dict()' in health_block
    assert "ready_for_real_data else 503" not in health_block


def test_health_is_degraded_by_postgres_not_redis_unavailability() -> None:
    source = _source()

    health_block = source.split('@app.get("/health"', 1)[1].split(
        '@app.get("/ready"',
        1,
    )[0]
    postgres_block = health_block.split(
        "checks[\"postgres\"] = \"error\"",
        1,
    )[1]
    redis_block = health_block.split(
        "checks[\"redis\"] = \"unavailable\"",
        1,
    )[1]

    assert "overall_ok = False" in postgres_block.split(
        "try:",
        1,
    )[0]
    assert "overall_ok = False" not in redis_block.split(
        "payload =",
        1,
    )[0]
    assert "status_code = 200 if overall_ok else 503" in health_block
