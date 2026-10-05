"""Dedicated synthetic Treasury price seed for certification issue #322/#303."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.certification.portfolio_seed_asset_policy import (
    SyntheticAssetIdentity,
    assert_persisted_asset_identity,
    build_synthetic_asset_plan,
)
from app.certification.portfolio_seed_contract import SyntheticSeedContractError
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

SYNTHETIC_TREASURY_PRICE_SOURCE = "synthetic-certification"
_TREASURY_TYPE = AssetType.TESOURO_DIRETO.value


@dataclass(frozen=True)
class SyntheticTreasuryPriceSeedResult:
    created: int
    reused: int


def _price_timestamp(as_of: object) -> datetime:
    try:
        return datetime.fromisoformat(f"{as_of}T00:00:00+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise SyntheticSeedContractError("synthetic treasury price as_of is invalid") from exc


def _expected_treasury_price(
    fixture: dict,
) -> tuple[SyntheticAssetIdentity, Decimal, datetime]:
    plan = build_synthetic_asset_plan(fixture)
    treasury = [identity for identity in plan.values() if identity.asset_type == _TREASURY_TYPE]
    if len(treasury) != 1:
        raise SyntheticSeedContractError("synthetic fixture must own exactly one treasury asset")

    market_prices = fixture.get("market_prices")
    if not isinstance(market_prices, dict):
        raise SyntheticSeedContractError("synthetic market prices contract is invalid")
    prices = market_prices.get("prices")
    if not isinstance(prices, dict):
        raise SyntheticSeedContractError("synthetic market prices contract is invalid")

    identity = treasury[0]
    raw_close = prices.get(identity.source_ticker)
    if raw_close is None:
        raise SyntheticSeedContractError(
            f"synthetic treasury price missing for {identity.source_ticker}"
        )
    close = Decimal(str(raw_close))
    if close <= 0:
        raise SyntheticSeedContractError("synthetic treasury price must be positive")
    return identity, close, _price_timestamp(market_prices.get("as_of"))


async def seed_synthetic_treasury_price(
    db: AsyncSession,
) -> SyntheticTreasuryPriceSeedResult:
    """Persist one deterministic Treasury price without calling external providers."""
    fixture = load_portfolio_synthetic_certification_fixture()
    identity, expected_close, timestamp = _expected_treasury_price(fixture)

    asset_columns = Asset.__table__.c
    asset_result = await db.execute(
        select(Asset).where(
            asset_columns.ticker == identity.ticker,
            asset_columns.asset_type == identity.asset_type,
        )
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        raise SyntheticSeedContractError(
            f"synthetic treasury asset {identity.ticker} must be seeded before price"
        )

    asset_ticker = str(asset.ticker)
    asset_type = str(asset.asset_type)
    asset_name = str(asset.name) if asset.name is not None else None
    asset_provider = str(asset.provider) if asset.provider is not None else None
    asset_provider_symbol = (
        str(asset.provider_symbol) if asset.provider_symbol is not None else None
    )
    asset_provider_status = (
        str(asset.provider_status) if asset.provider_status is not None else None
    )
    asset_currency = str(asset.currency or "").strip().upper()
    asset_id = int(asset.id)

    assert_persisted_asset_identity(
        ticker=asset_ticker,
        asset_type=asset_type,
        name=asset_name,
        provider=asset_provider,
        provider_symbol=asset_provider_symbol,
        provider_status=asset_provider_status,
        expected=identity,
    )
    if asset_currency != "BRL":
        raise SyntheticSeedContractError(
            f"synthetic treasury asset {identity.ticker} must use BRL currency"
        )

    price_columns = AssetPrice.__table__.c
    existing_result = await db.execute(
        select(AssetPrice).where(price_columns.asset_id == asset_id)
    )
    existing = list(existing_result.scalars().all())
    if existing:
        if len(existing) != 1:
            raise SyntheticSeedContractError(
                f"synthetic treasury price collision for {identity.ticker}; history is not canonical"
            )
        row = existing[0]
        if (
            row.timestamp != timestamp
            or Decimal(str(row.close)) != expected_close
            or str(row.source) != SYNTHETIC_TREASURY_PRICE_SOURCE
            or row.open is not None
            or row.high is not None
            or row.low is not None
            or row.volume is not None
        ):
            raise SyntheticSeedContractError(
                f"synthetic treasury price collision for {identity.ticker}; existing row is not canonical"
            )
        return SyntheticTreasuryPriceSeedResult(created=0, reused=1)

    db.add(
        AssetPrice(
            asset_id=asset_id,
            timestamp=timestamp,
            close=expected_close,
            source=SYNTHETIC_TREASURY_PRICE_SOURCE,
        )
    )
    await db.commit()
    return SyntheticTreasuryPriceSeedResult(created=1, reused=0)
