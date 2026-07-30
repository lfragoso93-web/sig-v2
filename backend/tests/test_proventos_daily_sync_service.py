"""Cobertura do universo operacional da sincronização diária de Proventos."""
from datetime import date
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.services import proventos_daily_sync_service
from app.services.proventos_daily_sync_service import (
    load_proventos_sync_pairs,
    run_daily_proventos_sync,
)


async def _make_transaction(
    db: AsyncSession,
    portfolio_id: int,
    ticker: str,
    asset_type: str,
) -> None:
    db.add(
        Transaction(
            portfolio_id=portfolio_id,
            ticker=ticker,
            asset_type=asset_type,
            operation=OperationType.buy,
            quantity=10,
            price=10,
            date=date(2024, 1, 1),
        )
    )
    await db.flush()


@pytest.mark.asyncio
async def test_daily_sync_defaults_to_the_global_asset_catalog(
    db: AsyncSession,
):
    db.add_all(
        [
            Asset(ticker="PETR4", name="PETR4", asset_type="ACAO", currency="BRL"),
            Asset(ticker="MXRF11", name="MXRF11", asset_type="FII", currency="BRL"),
            Asset(ticker="BOVA11", name="BOVA11", asset_type="ETF_NACIONAL", currency="BRL"),
            Asset(ticker="AAPL34", name="AAPL34", asset_type="BDR", currency="BRL"),
            Asset(ticker="BBAS3", name="BBAS3", asset_type="ACAO", currency="BRL"),
            Asset(ticker="PETR4F", name="PETR4F", asset_type="ACAO", currency="BRL"),
            Asset(ticker="BTC", name="BTC", asset_type="CRIPTO", currency="BRL"),
        ]
    )
    await db.flush()

    pairs, skipped = await load_proventos_sync_pairs(db)

    assert pairs == [
        ("BBAS3", "ACAO"),
        ("PETR4", "ACAO"),
        ("AAPL34", "BDR"),
        ("BOVA11", "ETF_NACIONAL"),
        ("MXRF11", "FII"),
    ]
    assert skipped == 1


@pytest.mark.asyncio
async def test_daily_sync_allows_explicit_held_scope(
    db: AsyncSession,
    portfolio: Portfolio,
):
    await _make_transaction(db, portfolio.id, "PETR4", "ACAO")
    await _make_transaction(db, portfolio.id, "MXRF11", "FII")
    await _make_transaction(db, portfolio.id, "BOVA11", "ETF_NACIONAL")
    await _make_transaction(db, portfolio.id, "AAPL34", "BDR")
    await _make_transaction(db, portfolio.id, "PETR4F", "ACAO")
    await _make_transaction(db, portfolio.id, "BTC", "CRIPTO")

    db.add(
        Asset(
            ticker="BBAS3",
            name="BBAS3",
            asset_type="ACAO",
            currency="BRL",
        )
    )
    await db.flush()

    pairs, skipped = await load_proventos_sync_pairs(
        db,
        only_held=True,
    )

    assert pairs == [
        ("PETR4", "ACAO"),
        ("AAPL34", "BDR"),
        ("BOVA11", "ETF_NACIONAL"),
        ("MXRF11", "FII"),
    ]
    assert skipped == 1


@pytest.mark.asyncio
async def test_daily_sync_does_not_materialize_portfolio_dividends(
    db: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    db.add(
        Asset(
            ticker="PETR4",
            name="PETR4",
            asset_type="ACAO",
            currency="BRL",
        )
    )
    await db.flush()

    sync_events = AsyncMock(return_value=(True, 3))
    invalidate = AsyncMock(return_value=2)

    class _SessionContext:
        async def __aenter__(self):
            return db

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        proventos_daily_sync_service,
        "_sync_asset_events",
        sync_events,
    )
    monkeypatch.setattr(
        proventos_daily_sync_service,
        "_invalidate_affected_portfolios",
        invalidate,
    )
    monkeypatch.setattr(
        "app.core.database.AsyncSessionLocal",
        _SessionContext,
    )

    result = await run_daily_proventos_sync(db, concurrency=1)

    assert result.assets_synced == 1
    assert result.historical_events == 3
    assert result.materialized == 0
    assert result.portfolios_invalidated == 2
    sync_events.assert_awaited_once_with(db, "PETR4", "ACAO")
    invalidate.assert_awaited_once_with(db, ["PETR4"])
