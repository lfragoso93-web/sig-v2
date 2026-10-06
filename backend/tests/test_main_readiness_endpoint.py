import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app import main
from app.services import real_data_readiness_report, real_data_runtime_identity
from app.services.real_data_runtime_identity import RealDataRuntimeIdentityError

MAIN_PATH = Path(__file__).resolve().parents[1] / "app" / "main.py"


def _source() -> str:
    return MAIN_PATH.read_text(encoding="utf-8")


def test_main_exposes_separate_health_and_readiness_endpoints() -> None:
    source = _source()

    assert '@app.get("/health"' in source
    assert '@app.get("/ready"' in source
    assert "ready_for_real_data" in source
    assert "resolve_real_data_runtime_identity" in source
    assert "build_real_data_readiness_report" in source


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


class _SessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


def test_ready_fails_closed_when_runtime_identity_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "AsyncSessionLocal", _SessionContext)
    monkeypatch.setattr(
        real_data_runtime_identity,
        "resolve_real_data_runtime_identity",
        AsyncMock(side_effect=RealDataRuntimeIdentityError("missing identity")),
    )
    report = AsyncMock()
    monkeypatch.setattr(
        real_data_readiness_report,
        "build_real_data_readiness_report",
        report,
    )

    response = asyncio.run(main.ready())
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["ready_for_real_data"] is False
    assert payload["certification"]["status"] == "runtime_identity_error"
    report.assert_not_awaited()


def test_ready_uses_persisted_report_as_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "AsyncSessionLocal", _SessionContext)
    identity = object()
    monkeypatch.setattr(
        real_data_runtime_identity,
        "resolve_real_data_runtime_identity",
        AsyncMock(return_value=identity),
    )
    payload = {
        "bootstrap_complete": False,
        "certification": {"status": "certified", "ready_for_real_data": True},
        "eligible_for_activation": True,
        "activation_required": False,
        "ready_for_real_data": True,
    }
    monkeypatch.setattr(
        real_data_readiness_report,
        "build_real_data_readiness_report",
        AsyncMock(return_value=SimpleNamespace(to_dict=lambda: payload)),
    )

    response = asyncio.run(main.ready())

    assert response.status_code == 200
    assert json.loads(response.body) == payload
