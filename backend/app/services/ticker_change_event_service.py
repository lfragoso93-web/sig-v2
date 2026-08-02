"""Persistencia de trocas simples de ticker e aliases historicos."""

import json
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_alias import AssetAlias
from app.models.corporate_event import CorporateEvent, CorporateEventStatus, CorporateEventType
from app.services.ticker_resolution_service import ResolvedTicker


def _event_key(portfolio_id: int, old_ticker: str, new_ticker: str, effective_date: date) -> str:
    return f"ticker-change:{portfolio_id}:{old_ticker}:{new_ticker}:{effective_date.isoformat()}"


async def register_ticker_change(
    db: AsyncSession,
    *,
    portfolio_id: int,
    old_asset: Asset,
    resolution: ResolvedTicker,
) -> CorporateEvent | None:
    if not resolution.changed or resolution.effective_date is None:
        return None
    if resolution.requested_ticker == resolution.current_ticker:
        return None

    current_result = await db.execute(
        select(Asset).where(
            Asset.ticker == resolution.current_ticker,
            Asset.asset_type == old_asset.asset_type,
        )
    )
    current_asset = current_result.scalar_one_or_none()
    if current_asset is None:
        current_asset = Asset(
            ticker=resolution.current_ticker,
            asset_type=old_asset.asset_type,
            currency=old_asset.currency,
        )
        db.add(current_asset)
        await db.flush()

    alias_result = await db.execute(
        select(AssetAlias).where(
            AssetAlias.alias_ticker == resolution.requested_ticker,
            AssetAlias.asset_type == str(old_asset.asset_type),
        )
    )
    alias = alias_result.scalar_one_or_none()
    if alias is None:
        db.add(
            AssetAlias(
                asset_id=current_asset.id,
                alias_ticker=resolution.requested_ticker,
                asset_type=str(old_asset.asset_type),
                effective_from=resolution.effective_date,
                source_provider="market_data_provider",
            )
        )
        await db.flush()

    event_key = _event_key(
        portfolio_id,
        resolution.requested_ticker,
        resolution.current_ticker,
        resolution.effective_date,
    )
    event_result = await db.execute(
        select(CorporateEvent).where(CorporateEvent.brapi_event_id == event_key)
    )
    event = event_result.scalar_one_or_none()
    if event is not None:
        return event

    event = CorporateEvent(
        asset_id=old_asset.id,
        portfolio_id=portfolio_id,
        ticker=resolution.requested_ticker,
        event_type=CorporateEventType.TICKER_CHANGE,
        status=CorporateEventStatus.PENDENTE,
        event_date=resolution.effective_date,
        ratio=Decimal(1),
        description=f"Ticker alterado para {resolution.current_ticker}",
        brapi_event_id=event_key,
        raw_data=json.dumps(
            {
                "old_ticker": resolution.requested_ticker,
                "new_ticker": resolution.current_ticker,
                "effective_date": resolution.effective_date.isoformat(),
            }
        ),
        reconciliation_status="UNRECONCILED",
        requires_review=True,
        source_provider="ticker_resolution",
        source_event_id=event_key,
        is_canonical=True,
        effective_date=resolution.effective_date,
        quantity_factor=Decimal(1),
        currency="BRL",
    )
    db.add(event)
    await db.flush()
    return event
