"""Synthetic AssetPrice seed for certification issue #318/#303."""

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
from app.models.asset import Asset
from app.models.asset_price import AssetPrice

SYNTHETIC_MARKET_PRICE_SOURCE = "synthetic-certification"
GENERIC_MARKET_PRICE_ASSET_TYPES = frozenset(
    {"ACAO", "FII", "ETF_NACIONAL", "BDR", "CRIPTO"}
)


@dataclass(frozen=True)
class SyntheticMarketPriceSeedResult:
    created: int
    reused: int


def _market_timestamp(as_of: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(f"{as_of}T00:00:00+00:00")
    except ValueError as exc:
        raise SyntheticSeedContractError("synthetic market price as_of is invalid") from exc
    return parsed.astimezone(timezone.utc)


def _expected_generic_prices(
    fixture: dict,
    plan: dict[str, SyntheticAssetIdentity],
) -> dict[str, tuple[SyntheticAssetIdentity, Decimal]]:
    market_prices = fixture.get("market_prices")
    if not isinstance(market_prices, dict):
        raise SyntheticSeedContractError("synthetic market prices contract is invalid")
    raw_prices = market_prices.get("prices")
    if not isinstance(raw_prices, dict):
        raise SyntheticSeedContractError("synthetic market prices contract is invalid")

    expected: dict[str, tuple[SyntheticAssetIdentity, Decimal]] = {}
    for source_ticker, raw_close in raw_prices.items():
        normalized = str(source_ticker).strip().upper()
        identity = plan.get(normalized)
        if identity is None:
            raise SyntheticSeedContractError(
                f"market price ticker {normalized} has no synthetic asset owner"
            )
        if identity.asset_type not in GENERIC_MARKET_PRICE_ASSET_TYPES:
            continue
        expected[identity.ticker] = (identity, Decimal(str(raw_close)))

    expected_types = {identity.asset_type for identity, _ in expected.values()}
    missing_types = GENERIC_MARKET_PRICE_ASSET_TYPES - expected_types
    if missing_types:
        raise SyntheticSeedContractError(
            "synthetic generic market prices are incomplete for asset types: "
            + ", ".join(sorted(missing_types))
        )
    return expected


async def _load_owned_assets(
    db: AsyncSession,
    expected: dict[str, tuple[SyntheticAssetIdentity, Decimal]],
) -> dict[str, Asset]:
    assets: dict[str, Asset] = {}
    for ticker, (identity, _) in expected.items():
        result = await db.execute(
            select(Asset).where(
                Asset.ticker == identity.ticker,
                Asset.asset_type == identity.asset_type,
            )
        )
        asset = result.scalar_one_or_none()
        if asset is None:
            raise SyntheticSeedContractError(
                f"synthetic market price asset {ticker} must be seeded before prices"
            )
        assert_persisted_asset_identity(
            ticker=asset.ticker,
            asset_type=asset.asset_type,
            name=asset.name,
            provider=asset.provider,
            provider_symbol=asset.provider_symbol,
            provider_status=asset.provider_status,
            expected=identity,
        )
        assets[ticker] = asset
    return assets


async def seed_generic_market_prices(db: AsyncSession) -> SyntheticMarketPriceSeedResult:
    """Seed deterministic prices for generic market assets only.

    Treasury and fixed-income aliases are intentionally excluded; their valuation
    must remain on dedicated engines and must not be masked by AssetPrice fallback.
    """
    fixture = load_portfolio_synthetic_certification_fixture()
    plan = build_synthetic_asset_plan(fixture)
    expected = _expected_generic_prices(fixture, plan)
    market_timestamp = _market_timestamp(str(fixture["market_prices"]["as_of"]))
    assets = await _load_owned_assets(db, expected)

    asset_ids = [asset.id for asset in assets.values()]
    existing_result = await db.execute(
        select(AssetPrice).where(AssetPrice.asset_id.in_(asset_ids))
    )
    existing_rows = list(existing_result.scalars().all())

    by_asset_id = {asset.id: ticker for ticker, asset in assets.items()}
    reused_tickers: set[str] = set()
    for row in existing_rows:
        ticker = by_asset_id.get(row.asset_id)
        if ticker is None:
            raise SyntheticSeedContractError("unexpected synthetic market price asset")
        _, expected_close = expected[ticker]
        if (
            row.timestamp != market_timestamp
            or Decimal(row.close) != expected_close
            or row.source != SYNTHETIC_MARKET_PRICE_SOURCE
            or row.open is not None
            or row.high is not None
            or row.low is not None
            or row.volume is not None
            or ticker in reused_tickers
        ):
            raise SyntheticSeedContractError(
                f"synthetic market price collision for {ticker}; existing row is not canonical"
            )
        reused_tickers.add(ticker)

    created = 0
    for ticker, asset in assets.items():
        if ticker in reused_tickers:
            continue
        _, close = expected[ticker]
        db.add(
            AssetPrice(
                asset_id=asset.id,
                timestamp=market_timestamp,
                close=close,
                source=SYNTHETIC_MARKET_PRICE_SOURCE,
            )
        )
        created += 1

    if created:
        await db.commit()

    return SyntheticMarketPriceSeedResult(
        created=created,
        reused=len(reused_tickers),
    )
