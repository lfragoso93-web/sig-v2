"""Testes do inventário read-only usado antes da migração de proventos."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.dividends_sync_job import DividendsSyncJob
from app.models.portfolio import Portfolio
from app.services.proventos_model_audit_service import audit_proventos_model


async def _event(db: AsyncSession) -> AssetDividend:
    asset = Asset(
        ticker="PETR4",
        name="PETR4",
        asset_type="ACAO",
        currency="BRL",
    )
    db.add(asset)
    await db.flush()
    event = AssetDividend(
        asset_id=asset.id,
        record_date=date(2026, 1, 9),
        ex_date=date(2026, 1, 12),
        payment_date=date(2026, 1, 30),
        value_per_unit=Decimal("1.25"),
        dividend_type=DividendType.DIVIDENDO,
        source="test",
    )
    db.add(event)
    await db.flush()
    return event


def _right(
    portfolio_id: int,
    event_id: int | None,
    *,
    canonical_date: date | None = date(2026, 1, 12),
    legacy_date: date | None = date(2026, 1, 12),
    canonical_payment: date | None = date(2026, 1, 30),
    legacy_payment: date | None = date(2026, 1, 30),
    canonical_quantity: Decimal | None = Decimal("10"),
    legacy_quantity: Decimal | None = Decimal("10"),
    canonical_value: Decimal | None = Decimal("1.25"),
    legacy_value: Decimal | None = Decimal("1.25"),
) -> Dividend:
    return Dividend(
        portfolio_id=portfolio_id,
        asset_dividend_id=event_id,
        ticker="PETR4",
        ex_date=canonical_date,
        date_ex=legacy_date,
        payment_date=canonical_payment,
        date_pagamento=legacy_payment,
        quantity=canonical_quantity,
        quantity_on_date=legacy_quantity,
        value_per_unit=canonical_value,
        value_per_share=legacy_value,
        total_value=Decimal("12.50"),
        net_value=Decimal("12.50"),
        total_received=Decimal("12.50"),
        dividend_type=DividendType.DIVIDENDO.value,
        status=DividendStatus.RECEBIDO,
    )


@pytest.mark.asyncio
async def test_audit_reports_clean_canonical_materialization(
    db: AsyncSession,
    portfolio: Portfolio,
):
    event = await _event(db)
    db.add(_right(portfolio.id, event.id))
    await db.flush()

    report = await audit_proventos_model(db)

    assert report.to_dict() == {
        "asset_events": 1,
        "portfolio_rights": 1,
        "unlinked_portfolio_rights": 0,
        "duplicate_materialization_groups": 0,
        "ex_date_mismatches": 0,
        "payment_date_mismatches": 0,
        "quantity_mismatches": 0,
        "value_per_unit_mismatches": 0,
        "legacy_sync_job_rows": 0,
    }


@pytest.mark.asyncio
async def test_audit_exposes_legacy_risks_without_mutating_rows(
    db: AsyncSession,
    portfolio: Portfolio,
):
    event = await _event(db)
    canonical = _right(portfolio.id, event.id)
    divergent = _right(
        portfolio.id,
        event.id,
        legacy_date=date(2026, 1, 13),
        legacy_payment=date(2026, 2, 2),
        legacy_quantity=Decimal("9"),
        legacy_value=Decimal("1.20"),
    )
    legacy_only = _right(
        portfolio.id,
        None,
        canonical_date=None,
        canonical_payment=None,
        canonical_quantity=None,
        canonical_value=None,
    )
    job = DividendsSyncJob(job_name="fii_dividends_bootstrap")
    db.add_all([canonical, divergent, legacy_only, job])
    await db.flush()

    report = await audit_proventos_model(db)

    assert report.asset_events == 1
    assert report.portfolio_rights == 3
    assert report.unlinked_portfolio_rights == 1
    assert report.duplicate_materialization_groups == 1
    assert report.ex_date_mismatches == 2
    assert report.payment_date_mismatches == 2
    assert report.quantity_mismatches == 2
    assert report.value_per_unit_mismatches == 2
    assert report.legacy_sync_job_rows == 1
    assert canonical.asset_dividend_id == event.id
    assert legacy_only.asset_dividend_id is None
