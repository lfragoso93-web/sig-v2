"""Tests for the read-only physical residue inventory."""

from datetime import date
from decimal import Decimal

import pytest
from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.portfolio import Portfolio
from app.services.proventos_model_audit_service import audit_proventos_model
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_audit_counts_only_physical_residues_without_mutating_rows(
    db: AsyncSession,
    portfolio: Portfolio,
) -> None:
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
    right = Dividend(
        portfolio_id=portfolio.id,
        ticker="PETR4",
        date_ex=date(2026, 1, 12),
        date_pagamento=date(2026, 1, 30),
        quantity_on_date=Decimal(10),
        value_per_share=Decimal("1.25"),
        total_received=Decimal("12.50"),
        dividend_type=DividendType.DIVIDENDO.value,
        status=DividendStatus.RECEBIDO,
    )
    db.add_all([event, right])
    await db.flush()

    report = await audit_proventos_model(db)

    assert report.to_dict() == {
        "asset_events": 1,
        "legacy_dividend_rows": 1,
    }
    assert not db.dirty
