from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import UserRole
from app.routers.recommended_portfolios import router as recommended_portfolios_router
from app.services.recommended_portfolio_service import RecommendedPortfolioService
from app.schemas.recommended_portfolio import RecommendedPortfolioSimulationRequest


def _client() -> TestClient:
    app = FastAPI()
    db = AsyncMock()
    app.include_router(recommended_portfolios_router, prefix="/api/v1/recommended-portfolios")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1,
        role=UserRole.user,
        email="user@test.com",
    )
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_list_recommended_portfolios():
    client = _client()
    resp = client.get("/api/v1/recommended-portfolios")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    strategies = {item["strategy"] for item in data}
    assert strategies == {"patrimonio", "proventos", "performance"}

    for p in data:
        assert p["title"]
        assert p["thesis"]
        assert len(p["classes"]) > 0
        total_weight = sum(c["target_weight_pct"] for c in p["classes"])
        assert abs(total_weight - 100.0) < 0.01


@pytest.mark.parametrize("strategy", ["patrimonio", "proventos", "performance"])
def test_get_recommended_portfolio_by_strategy(strategy: str):
    client = _client()
    resp = client.get(f"/api/v1/recommended-portfolios/{strategy}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy"] == strategy
    assert data["diversification_score"] >= 80

    # Ensure every class has assets
    for c in data["classes"]:
        assert len(c["assets"]) > 0
        for a in c["assets"]:
            assert a["ticker"]
            assert a["name"]
            assert a["current_price"] > 0
            assert a["reason"]


def test_get_recommended_portfolio_not_found():
    client = _client()
    resp = client.get("/api/v1/recommended-portfolios/nao_existe")
    assert resp.status_code == 404
    assert "não encontrada" in resp.json()["detail"]


def test_simulate_contribution_default_weights():
    client = _client()
    payload = {
        "strategy": "proventos",
        "total_amount": 10000.0,
    }
    resp = client.post("/api/v1/recommended-portfolios/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy"] == "proventos"
    assert data["total_amount"] == 10000.0

    total_allocated = sum(
        asset["allocated_amount"]
        for c in data["classes"]
        for asset in c["assets"]
    )
    assert abs(total_allocated - 10000.0) < 0.05
    assert len(data["classes"]) >= 4


def test_simulate_contribution_custom_weights():
    client = _client()
    payload = {
        "strategy": "patrimonio",
        "total_amount": 5000.0,
        "custom_class_weights": {
            "ACAO": 50.0,
            "FII": 50.0,
        },
    }
    resp = client.post("/api/v1/recommended-portfolios/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_amount"] == 5000.0

    acao_class = next(c for c in data["classes"] if c["asset_type"] == "ACAO")
    fii_class = next(c for c in data["classes"] if c["asset_type"] == "FII")

    assert abs(acao_class["target_weight_pct"] - 50.0) < 0.01
    assert abs(fii_class["target_weight_pct"] - 50.0) < 0.01
    assert abs(acao_class["allocated_amount"] - 2500.0) < 1.0
    assert abs(fii_class["allocated_amount"] - 2500.0) < 1.0


def test_simulate_contribution_invalid_amount():
    client = _client()
    resp = client.post(
        "/api/v1/recommended-portfolios/simulate",
        json={"strategy": "patrimonio", "total_amount": -100.0},
    )
    assert resp.status_code == 422
