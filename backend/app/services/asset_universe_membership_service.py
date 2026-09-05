"""Persistência DB-first de associações a universos operacionais."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_universe_membership import AssetUniverseMembership
from app.services.crypto_supported_universe_service import SupportedCrypto

CRYPTO_TOP100_UNIVERSE_KEY = "crypto_top100_market_cap"
CRYPTO_TOP100_UNIVERSE_SOURCE = "coingecko_market_cap_intersect_brapi"
CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY = "crypto_synthetic_certification"
CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_SOURCE = "synthetic-certification"


async def replace_crypto_candidate_memberships(
    db: AsyncSession,
    candidates: list[SupportedCrypto],
) -> int:
    """Substitui atomicamente a fotografia persistida do universo candidato CRIPTO."""
    by_ticker = {item.ticker.upper(): item for item in candidates}
    if len(by_ticker) != len(candidates):
        raise ValueError("candidate crypto universe contains duplicate tickers")

    assets_by_ticker: dict[str, Asset] = {}
    if by_ticker:
        rows = await db.execute(
            select(Asset)
            .where(Asset.asset_type == AssetType.CRIPTO.value)
            .where(func.upper(Asset.ticker).in_(set(by_ticker)))
        )
        assets_by_ticker = {asset.ticker.upper(): asset for asset in rows.scalars()}

    missing = sorted(set(by_ticker) - set(assets_by_ticker))
    if missing:
        raise RuntimeError(
            "candidate crypto assets must be persisted before universe membership: "
            + ", ".join(missing)
        )

    await db.execute(
        delete(AssetUniverseMembership).where(
            AssetUniverseMembership.universe_key == CRYPTO_TOP100_UNIVERSE_KEY
        )
    )

    refreshed_at = datetime.now(timezone.utc)
    for ticker, candidate in by_ticker.items():
        db.add(
            AssetUniverseMembership(
                asset_id=assets_by_ticker[ticker].id,
                universe_key=CRYPTO_TOP100_UNIVERSE_KEY,
                rank=candidate.market_cap_rank,
                source=CRYPTO_TOP100_UNIVERSE_SOURCE,
                refreshed_at=refreshed_at,
            )
        )

    return len(by_ticker)
