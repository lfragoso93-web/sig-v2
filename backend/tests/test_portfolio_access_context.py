"""Authorization boundary for portfolio-scoped data access."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from app.core.access_context import PortfolioAccessContext, PortfolioAccessDenied
from app.repositories.portfolio_access_repository import get_accessible_portfolio
from app.routers import dividends as dividends_router
from app.services.dividend_service import READ_PORTFOLIO_DIVIDENDS, list_dividends


def _user_access(*, user_id: int = 3, portfolio_id: int = 7) -> PortfolioAccessContext:
    return PortfolioAccessContext.for_user(
        user_id=user_id,
        portfolio_id=portfolio_id,
        permissions=frozenset({READ_PORTFOLIO_DIVIDENDS}),
        request_id="request-348",
    )


def test_user_context_requires_explicit_identity_scope_and_permission() -> None:
    access = _user_access()

    assert access.user_id == 3
    assert access.portfolio_id == 7
    assert access.request_id == "request-348"
    assert READ_PORTFOLIO_DIVIDENDS in access.permissions

    with pytest.raises(ValueError, match="positive user_id"):
        PortfolioAccessContext.for_user(
            user_id=0,
            portfolio_id=7,
            permissions=frozenset({READ_PORTFOLIO_DIVIDENDS}),
        )


def test_system_context_requires_explicit_purpose_and_never_impersonates_user() -> None:
    with pytest.raises(ValueError, match="explicit purpose"):
        PortfolioAccessContext.for_system(
            portfolio_id=7,
            permissions=frozenset({READ_PORTFOLIO_DIVIDENDS}),
            purpose=" ",
        )

    access = PortfolioAccessContext.for_system(
        portfolio_id=7,
        permissions=frozenset({READ_PORTFOLIO_DIVIDENDS}),
        purpose="certification-readonly-reconciliation",
    )

    assert access.user_id is None
    assert access.purpose == "certification-readonly-reconciliation"


@pytest.mark.asyncio
async def test_cross_user_portfolio_access_is_denied_before_sensitive_read() -> None:
    db = AsyncMock()
    ownership_result = Mock()
    ownership_result.scalar_one_or_none.return_value = None
    db.execute.return_value = ownership_result

    with pytest.raises(
        PortfolioAccessDenied,
        match="Carteira nao encontrada ou sem permissao",
    ):
        await list_dividends(db, _user_access(user_id=3, portfolio_id=99))

    assert db.execute.await_count == 1
    ownership_query = str(db.execute.await_args.args[0])
    assert "portfolios.id" in ownership_query
    assert "portfolios.user_id" in ownership_query


@pytest.mark.asyncio
async def test_repository_rejects_missing_permission_without_querying_database() -> None:
    db = AsyncMock()
    access = PortfolioAccessContext.for_user(
        user_id=3,
        portfolio_id=7,
        permissions=frozenset({"portfolio:positions:read"}),
    )

    with pytest.raises(PortfolioAccessDenied):
        await get_accessible_portfolio(
            db,
            access,
            required_permission=READ_PORTFOLIO_DIVIDENDS,
        )

    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_explicit_system_context_uses_scoped_portfolio_lookup() -> None:
    db = AsyncMock()
    result = Mock()
    portfolio = SimpleNamespace(id=7, user_id=3)
    result.scalar_one_or_none.return_value = portfolio
    db.execute.return_value = result
    access = PortfolioAccessContext.for_system(
        portfolio_id=7,
        permissions=frozenset({READ_PORTFOLIO_DIVIDENDS}),
        purpose="certification-readonly-reconciliation",
    )

    resolved = await get_accessible_portfolio(
        db,
        access,
        required_permission=READ_PORTFOLIO_DIVIDENDS,
    )

    assert resolved is portfolio
    ownership_query = str(db.execute.await_args.args[0])
    assert "portfolios.id" in ownership_query
    where_clause = ownership_query.partition("WHERE")[2]
    assert "portfolios.user_id" not in where_clause


@pytest.mark.asyncio
async def test_http_controller_builds_user_context(monkeypatch) -> None:
    captured: list[PortfolioAccessContext] = []

    async def _list_dividends(db, access):
        captured.append(access)
        return []

    monkeypatch.setattr(dividends_router, "list_dividends", _list_dividends)

    result = await dividends_router.get_dividends(
        portfolio_id=7,
        db=AsyncMock(),
        current_user=SimpleNamespace(id=3),
    )

    assert result == []
    assert len(captured) == 1
    assert captured[0].user_id == 3
    assert captured[0].portfolio_id == 7
    assert captured[0].permissions == frozenset({READ_PORTFOLIO_DIVIDENDS})


@pytest.mark.asyncio
async def test_http_controller_hides_cross_portfolio_denial(monkeypatch) -> None:
    async def _deny(db, access):
        raise PortfolioAccessDenied("Carteira nao encontrada ou sem permissao")

    monkeypatch.setattr(dividends_router, "list_dividends", _deny)

    with pytest.raises(HTTPException) as exc_info:
        await dividends_router.get_dividends(
            portfolio_id=99,
            db=AsyncMock(),
            current_user=SimpleNamespace(id=3),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Carteira nao encontrada ou sem permissao"
