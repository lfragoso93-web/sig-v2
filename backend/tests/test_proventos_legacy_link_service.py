"""Testes do dry-run de vínculo entre direitos legados e eventos globais."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.portfolio import Portfolio
from app.services.proventos_legacy_link_service import (
    LegacyLinkStatus,
    dry_run_legacy_dividend_links,
)


async def _event(
    db: AsyncSession,
    *,
    ticker: str = "PETR4",
    asset_type: str = "ACAO",
    value: str = "1.25",
) -> AssetDividend:
    asset = Asset(
        ticker=ticker,
        name=ticker,
        asset_type=asset_type,
        currency="BRL",
    )
    db.add(asset)
    await db.flush()
    event = AssetDividend(
        asset_id=asset.id,
        record_date=date(2026, 1, 9),
        ex_date=date(2026, 1, 12),
        payment_date=date(2026, 1, 30),
        value_per_unit=Decimal(value),
        dividend_type=DividendType.DIVIDENDO,
        source="test",
    )
    db.add(event)
    await db.flush()
    return event


def _right(
    portfolio_id: int,
    *,
    event_id: int | None = None,
    ticker: str | None = "petr4",
    ex_date: date | None = date(2026, 1, 12),
    date_ex: date | None = date(2026, 1, 12),
    value: str = "1.25",
    legacy_value: str = "1.25",
    dividend_type: str = "Dividendos",
) -> Dividend:
    return Dividend(
        portfolio_id=portfolio_id,
        asset_dividend_id=event_id,
        ticker=ticker,
        ex_date=ex_date,
        date_ex=date_ex,
        payment_date=date(2026, 1, 30),
        date_pagamento=date(2026, 1, 30),
        quantity=Decimal("10"),
        quantity_on_date=Decimal("10"),
        value_per_unit=Decimal(value),
        value_per_share=Decimal(legacy_value),
        total_value=Decimal("12.50"),
        net_value=Decimal("12.50"),
        total_received=Decimal("12.50"),
        dividend_type=dividend_type,
        status=DividendStatus.RECEBIDO,
    )


@pytest.mark.asyncio
async def test_dry_run_matches_strict_identity_without_mutating_right(
    db: AsyncSession,
    portfolio: Portfolio,
):
    event = await _event(db)
    right = _right(portfolio.id)
    db.add(right)
    await db.flush()

    report = await dry_run_legacy_dividend_links(db)

    assert report.to_dict(include_details=False) == {
        "scanned": 1,
        "matched": 1,
        "no_candidate": 0,
        "ambiguous": 0,
        "legacy_divergence": 0,
        "invalid_identity": 0,
        "duplicate_right": 0,
    }
    assert report.decisions[0].candidate_event_ids == (event.id,)
    assert right.asset_dividend_id is None
    assert not db.dirty


@pytest.mark.asyncio
async def test_dry_run_separates_no_candidate_divergence_and_invalid_identity(
    db: AsyncSession,
    portfolio: Portfolio,
):
    await _event(db)
    no_candidate = _right(portfolio.id, value="9.99", legacy_value="9.99")
    divergent = _right(portfolio.id, date_ex=date(2026, 1, 13))
    invalid = _right(portfolio.id, ticker=None)
    db.add_all([no_candidate, divergent, invalid])
    await db.flush()

    report = await dry_run_legacy_dividend_links(db)
    statuses = {item.dividend_id: item.status for item in report.decisions}

    assert statuses[no_candidate.id] == LegacyLinkStatus.NO_CANDIDATE
    assert statuses[divergent.id] == LegacyLinkStatus.LEGACY_DIVERGENCE
    assert statuses[invalid.id] == LegacyLinkStatus.INVALID_IDENTITY


@pytest.mark.asyncio
async def test_dry_run_rejects_more_than_one_strict_candidate(
    db: AsyncSession,
    portfolio: Portfolio,
):
    first = await _event(db, asset_type="ACAO")
    second = await _event(db, asset_type="BDR")
    right = _right(portfolio.id)
    db.add(right)
    await db.flush()

    report = await dry_run_legacy_dividend_links(db)

    decision = report.decisions[0]
    assert decision.status == LegacyLinkStatus.AMBIGUOUS
    assert decision.candidate_event_ids == (first.id, second.id)


@pytest.mark.asyncio
async def test_dry_run_blocks_existing_and_provisional_duplicate_rights(
    db: AsyncSession,
    portfolio: Portfolio,
):
    event = await _event(db)
    linked = _right(portfolio.id, event_id=event.id)
    conflicts_with_linked = _right(portfolio.id)
    db.add_all([linked, conflicts_with_linked])
    await db.flush()

    report = await dry_run_legacy_dividend_links(db)

    assert report.decisions[0].status == LegacyLinkStatus.DUPLICATE_RIGHT

    await db.delete(linked)
    await db.flush()
    another_unlinked = _right(portfolio.id)
    db.add(another_unlinked)
    await db.flush()

    report = await dry_run_legacy_dividend_links(db)

    assert report.count(LegacyLinkStatus.DUPLICATE_RIGHT) == 2
