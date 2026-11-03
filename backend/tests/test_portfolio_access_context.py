"""Authorization boundary for portfolio-scoped data access."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.core.access_context import PortfolioAccessContext, PortfolioAccessDenied
from app.repositories.portfolio_access_repository import (
    get_accessible_portfolio,
    get_accessible_transaction,
)
from app.routers import dividends as dividends_router
from app.routers import transactions as transactions_router
from app.schemas.transaction import TransactionUpdate
from app.services.dividend_service import READ_PORTFOLIO_DIVIDENDS, list_dividends
from app.services.transaction_write_service import WRITE_PORTFOLIO_TRANSACTIONS


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


@pytest.mark.parametrize("principal_kind", ["user", "system", None])
def test_context_rejects_untyped_principal_kind(principal_kind) -> None:
    with pytest.raises(ValueError, match="AccessPrincipalKind"):
        PortfolioAccessContext(
            principal_kind=principal_kind,
            user_id=3,
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
async def test_transaction_repository_filters_transaction_by_portfolio_owner() -> None:
    db = AsyncMock()
    result = Mock()
    transaction = SimpleNamespace(id=41, portfolio_id=7)
    result.scalar_one_or_none.return_value = transaction
    db.execute.return_value = result
    access = PortfolioAccessContext.for_user(
        user_id=3,
        portfolio_id=7,
        permissions=frozenset({WRITE_PORTFOLIO_TRANSACTIONS}),
    )

    resolved = await get_accessible_transaction(
        db,
        access,
        transaction_id=41,
        required_permission=WRITE_PORTFOLIO_TRANSACTIONS,
    )

    assert resolved is transaction
    query = str(db.execute.await_args.args[0])
    assert "transactions.id" in query
    assert "transactions.portfolio_id" in query
    assert "portfolios.user_id" in query


@pytest.mark.asyncio
async def test_transaction_repository_rejects_missing_write_permission_without_query() -> None:
    db = AsyncMock()
    access = PortfolioAccessContext.for_user(
        user_id=3,
        portfolio_id=7,
        permissions=frozenset({READ_PORTFOLIO_DIVIDENDS}),
    )

    with pytest.raises(PortfolioAccessDenied):
        await get_accessible_transaction(
            db,
            access,
            transaction_id=41,
            required_permission=WRITE_PORTFOLIO_TRANSACTIONS,
        )

    db.execute.assert_not_awaited()


@pytest.mark.parametrize("endpoint", ["update_transaction", "delete_transaction"])
@pytest.mark.asyncio
async def test_transaction_mutations_return_404_for_nonpositive_portfolio_id(endpoint):
    db = AsyncMock()
    handler = getattr(transactions_router, endpoint)
    kwargs = {
        "portfolio_id": 0,
        "transaction_id": 41,
        "background_tasks": BackgroundTasks(),
        "db": db,
        "current_user": SimpleNamespace(id=3),
    }
    if endpoint == "update_transaction":
        kwargs["payload"] = TransactionUpdate(price=100)

    with pytest.raises(HTTPException) as exc_info:
        await handler(**kwargs)

    assert exc_info.value.status_code == 404
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
async def test_repository_fails_closed_for_unrecognized_principal() -> None:
    db = AsyncMock()
    access = object.__new__(PortfolioAccessContext)
    object.__setattr__(access, "principal_kind", "system")
    object.__setattr__(access, "portfolio_id", 7)
    object.__setattr__(access, "permissions", frozenset({READ_PORTFOLIO_DIVIDENDS}))

    with pytest.raises(PortfolioAccessDenied):
        await get_accessible_portfolio(
            db,
            access,
            required_permission=READ_PORTFOLIO_DIVIDENDS,
        )

    db.execute.assert_not_awaited()


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


def test_system_maintenance_declares_system_context() -> None:
    from app.services.portfolio_snapshot_twr_maintenance_service import (
        MAINTAIN_PORTFOLIO_SNAPSHOTS,
    )

    access = PortfolioAccessContext.for_system(
        portfolio_id=12,
        permissions=frozenset({MAINTAIN_PORTFOLIO_SNAPSHOTS}),
        purpose="background_nightly_twr_maintenance",
    )
    assert access.portfolio_id == 12
    assert access.user_id is None
    assert access.purpose == "background_nightly_twr_maintenance"
    assert MAINTAIN_PORTFOLIO_SNAPSHOTS in access.permissions
