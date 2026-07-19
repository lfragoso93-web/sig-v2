"""Cobertura do universo operacional da sincronização diária de Proventos."""
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.services.proventos_daily_sync_service import load_proventos_sync_pairs


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
async def test_daily_sync_defaults_to_held_national_assets(
    db: AsyncSession,
    portfolio: Portfolio,
):
    await _make_transaction(db, portfolio.id, "PETR4", "ACAO")
    await _make_transaction(db, portfolio.id, "MXRF11", "FII")
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

    pairs, skipped = await load_proventos_sync_pairs(db)

    assert pairs == [("PETR4", "ACAO"), ("MXRF11", "FII")]
    assert skipped == 1


@pytest.mark.asyncio
async def test_daily_sync_allows_explicit_full_catalog_scope(
    db: AsyncSession,
):
    db.add_all(
        [
            Asset(
                ticker="BBAS3",
                name="BBAS3",
                asset_type="ACAO",
                currency="BRL",
            ),
            Asset(
                ticker="KNRI11",
                name="KNRI11",
                asset_type="FII",
                currency="BRL",
            ),
        ]
    )
    await db.flush()

    pairs, skipped = await load_proventos_sync_pairs(
        db,
        only_held=False,
    )

    assert pairs == [("BBAS3", "ACAO"), ("KNRI11", "FII")]
    assert skipped == 0
