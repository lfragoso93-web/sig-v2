import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.access_context import (
    AccessPrincipalKind,
    PortfolioAccessContext,
    PortfolioAccessDenied,
)
from app.routers.proventos import _access_context
from app.services.proventos_service import (
    READ_PORTFOLIO_PROVENTOS,
    get_summary,
)


class _Result:
    def scalar_one_or_none(self):
        return None


def test_proventos_router_builds_user_context_and_rejects_invalid_ids():
    access = _access_context(7, SimpleNamespace(id=23))

    assert access.principal_kind is AccessPrincipalKind.USER
    assert access.user_id == 23
    assert access.portfolio_id == 7
    assert access.permissions == frozenset({READ_PORTFOLIO_PROVENTOS})

    with pytest.raises(HTTPException) as exc_info:
        _access_context(0, SimpleNamespace(id=23))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Carteira nao encontrada."


def test_all_proventos_routes_pass_access_context_to_the_service():
    source_path = Path(__file__).parents[1] / "app" / "routers" / "proventos.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    endpoints = {
        "proventos_summary": "get_summary",
        "list_proventos": "list_items",
        "proventos_historico_mensal": "get_monthly_history",
        "proventos_distribuicao": "get_distribution",
    }

    for endpoint_name, service_name in endpoints.items():
        endpoint = next(
            node
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == endpoint_name
        )
        calls = [
            node
            for node in ast.walk(endpoint)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == service_name
        ]
        assert len(calls) == 1
        assert isinstance(calls[0].args[1], ast.Name)
        assert calls[0].args[1].id == "access"


@pytest.mark.asyncio
async def test_proventos_service_denies_foreign_portfolio_before_projection(
    monkeypatch,
):
    db = AsyncMock()
    db.execute.return_value = _Result()
    projection = AsyncMock()
    monkeypatch.setattr(
        "app.services.proventos_service._get_summary_projection", projection
    )
    access = PortfolioAccessContext.for_user(
        user_id=23,
        portfolio_id=7,
        permissions=frozenset({READ_PORTFOLIO_PROVENTOS}),
    )

    with pytest.raises(PortfolioAccessDenied):
        await get_summary(db, access)

    projection.assert_not_awaited()


@pytest.mark.asyncio
async def test_proventos_service_rejects_missing_permission_without_query():
    db = AsyncMock()
    access = PortfolioAccessContext.for_user(
        user_id=23,
        portfolio_id=7,
        permissions=frozenset({"read:another_surface"}),
    )

    with pytest.raises(PortfolioAccessDenied):
        await get_summary(db, access)

    db.execute.assert_not_awaited()
