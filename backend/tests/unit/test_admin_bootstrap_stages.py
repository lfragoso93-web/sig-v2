"""Testes unitários para a Central de Bootstrap por etapas (Issue #253)."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.models.user import User
from app.routers.admin import require_superadmin
from app.services.system_bootstrap_service import (
    BOOTSTRAP_SCHEMA_VERSION,
    CANONICAL_BOOTSTRAP_STAGES,
    BootstrapStageResult,
    SystemBootstrapReport,
    run_system_bootstrap,
)
from app.services.system_bootstrap_trigger_service import (
    bootstrap_launch_reserved,
    reserve_system_bootstrap_launch,
    reset_bootstrap_launch_reservation_for_tests,
    run_reserved_system_bootstrap,
)
from app.services.system_readiness_service import (
    BootstrapReadinessState,
    get_bootstrap_readiness,
    reset_bootstrap_readiness_for_tests,
)

VALID_SHA = "a" * 40


def _mock_superadmin():
    user = User(
        id=1,
        email="superadmin@sgi.com",
        role="superadmin",
        is_active=True,
    )
    return user


@pytest.fixture(autouse=True)
def _reset_state():
    reset_bootstrap_readiness_for_tests()
    reset_bootstrap_launch_reservation_for_tests()
    yield
    reset_bootstrap_readiness_for_tests()
    reset_bootstrap_launch_reservation_for_tests()


@pytest.mark.asyncio
async def test_canonical_bootstrap_stages_inventory():
    """Garante que os 10 estágios canônicos estão inventariados."""
    stage_ids = [s.id for s in CANONICAL_BOOTSTRAP_STAGES]
    assert len(stage_ids) == 13
    expected = [
        "b3_baseline",
        "asset_catalog",
        "treasury_catalog",
        "treasury_reconciliation",
        "treasury_history",
        "asset_price_history",
        "benchmarks",
        "fx_rates",
        "asset_dividends",
        "corporate_events",
        "international_catalog",
        "international_price_history",
        "asset_fundamentals",
    ]
    assert stage_ids == expected


@pytest.mark.asyncio
async def test_admin_bootstrap_status_exposes_stages():
    """Status endpoint expõe a lista completa de estágios com metadados."""
    app.dependency_overrides[require_superadmin] = _mock_superadmin
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/admin/bootstrap/status")
        assert resp.status_code == 200
        data = resp.json()

        assert "stages" in data
        assert len(data["stages"]) == 13
        assert (
            data["schema_version"] is None
            or data["schema_version"] == BOOTSTRAP_SCHEMA_VERSION
        )
        assert data["launch_reserved"] is False
        assert data["ready_for_real_data"] is False

        first = data["stages"][0]
        assert first["id"] == "b3_baseline"
        assert first["status"] == "idle"
        assert first["provider_dependent"] is False
        assert first["destructive"] is False
        assert first["dependencies"] == []

        fx = next(s for s in data["stages"] if s["id"] == "fx_rates")
        assert fx["name"] == "Taxas de Câmbio PTAX"
        assert fx["provider_dependent"] is True
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trigger_selective_bootstrap():
    """Acionamento seletivo com stages válidos é aceito com 202."""
    app.dependency_overrides[require_superadmin] = _mock_superadmin
    with patch(
        "app.routers.admin_bootstrap.run_reserved_system_bootstrap",
        new=AsyncMock(),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/admin/bootstrap",
                json={
                    "commit_sha": VALID_SHA,
                    "stages": ["fx_rates", "benchmarks"],
                },
            )
            assert resp.status_code == 202
            data = resp.json()
            assert data["status"] == "accepted"
            assert data["commit_sha"] == VALID_SHA
            assert data["stages"] == ["fx_rates", "benchmarks"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trigger_invalid_stage_rejected():
    """Estágio inexistente retorna 400 Bad Request."""
    app.dependency_overrides[require_superadmin] = _mock_superadmin
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/admin/bootstrap",
            json={
                "commit_sha": VALID_SHA,
                "stages": ["invalid_stage_xyz"],
            },
        )
        assert resp.status_code == 400
        assert "Etapas desconhecidas" in resp.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trigger_conflict_when_already_reserved():
    """Tentativa concorrente de reserva retorna 409 Conflict."""
    assert reserve_system_bootstrap_launch(VALID_SHA) is True

    app.dependency_overrides[require_superadmin] = _mock_superadmin
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/admin/bootstrap",
            json={"commit_sha": VALID_SHA},
        )
        assert resp.status_code == 409
        assert "bootstrap global ja reservado" in resp.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_selective_execution_updates_stages_and_preserves_guardrails():
    """Execução seletiva atualiza apenas etapas selecionadas."""
    with patch(
        "app.services.system_bootstrap_service._bootstrap_benchmarks",
        new=AsyncMock(return_value="benchmarks imported=10"),
    ):
        report = await run_system_bootstrap(
            commit_sha=VALID_SHA,
            stages=["benchmarks"],
        )

    assert report.ok is True
    assert len(report.stages) == 1
    assert report.stages[0].name == "benchmarks"
    assert "imported=10" in report.stages[0].detail

    readiness = get_bootstrap_readiness()
    assert readiness.ready_for_real_data is False
    assert readiness.certified_for_real_data is False

    status_dict = readiness.to_dict()
    benchmarks_stage = next(
        s for s in status_dict["stages"] if s["id"] == "benchmarks"
    )
    assert benchmarks_stage["status"] == "success"
    assert "imported=10" in benchmarks_stage["detail"]

    # As outras etapas continuam idle
    b3_stage = next(
        s for s in status_dict["stages"] if s["id"] == "b3_baseline"
    )
    assert b3_stage["status"] == "idle"
