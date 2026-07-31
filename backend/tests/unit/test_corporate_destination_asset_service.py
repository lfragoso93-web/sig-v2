from datetime import date
from decimal import Decimal

import pytest
from app.models.asset import Asset, AssetType
from app.models.corporate_event import CorporateEvent
from app.services.corporate_destination_asset_service import (
    DestinationResolutionStatus,
    resolve_corporate_destination_asset,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def _asset(db: AsyncSession, ticker: str, *, isin: str | None = None) -> Asset:
    asset = Asset(
        ticker=ticker,
        name=ticker,
        asset_type=AssetType.ACAO.value,
        currency="BRL",
        isin_code=isin,
    )
    db.add(asset)
    await db.flush()
    return asset


async def _event(db: AsyncSession, source: Asset, **destination) -> CorporateEvent:
    event = CorporateEvent(
        asset_id=source.id,
        ticker=source.ticker,
        event_type="MERGER",
        status="DISCOVERED",
        reconciliation_status="REVIEW_REQUIRED",
        requires_review=True,
        source_provider="brapi",
        source_event_id=f"merger-{source.id}",
        is_canonical=True,
        effective_date=date(2026, 7, 1),
        quantity_factor=Decimal("0.5"),
        event_date=date(2026, 7, 1),
        ratio=Decimal("0.5"),
        currency="BRL",
        **destination,
    )
    db.add(event)
    await db.flush()
    return event


@pytest.mark.asyncio
async def test_resolves_and_binds_destination_by_isin(db: AsyncSession) -> None:
    source = await _asset(db, "OLD3")
    target = await _asset(db, "NEW3", isin="BRNEW3ACNOR1")
    event = await _event(db, source, destination_isin_code="brnew3acnor1")

    resolution = await resolve_corporate_destination_asset(db, event, bind=True)

    assert resolution.status is DestinationResolutionStatus.RESOLVED
    assert resolution.asset_id == target.id
    assert resolution.matched_by == ("isin_code",)
    assert event.destination_asset_id == target.id
    assert event.destination_ticker == "NEW3"


@pytest.mark.asyncio
async def test_combined_ticker_and_isin_must_identify_same_asset(
    db: AsyncSession,
) -> None:
    source = await _asset(db, "OLD3")
    await _asset(db, "NEW3", isin="BRNEW3ACNOR1")
    event = await _event(
        db,
        source,
        destination_ticker="NEW3",
        destination_isin_code="BRDIFFERENT00",
    )

    resolution = await resolve_corporate_destination_asset(db, event)

    assert resolution.status is DestinationResolutionStatus.NOT_FOUND
    assert event.destination_asset_id is None


@pytest.mark.asyncio
async def test_explicit_asset_id_conflicting_with_isin_is_rejected(
    db: AsyncSession,
) -> None:
    source = await _asset(db, "OLD3")
    target = await _asset(db, "NEW3", isin="BRNEW3ACNOR1")
    event = await _event(
        db,
        source,
        destination_asset_id=target.id,
        destination_isin_code="BRDIFFERENT00",
    )

    resolution = await resolve_corporate_destination_asset(db, event)

    assert resolution.status is DestinationResolutionStatus.CONFLICT
