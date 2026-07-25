"""Leitura auditável e estritamente read-only do estado do Tesouro Direto.

O módulo não sincroniza catálogo, não consulta provedores e não executa rebuild.
Ele apenas produz as contagens e a cobertura exigidas pelo contrato da Issue #208.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_alias import AssetAlias
from app.models.asset_price import AssetPrice
from app.services.pre_prod_treasury_seed_contract import (
    LEGACY_TREASURY_ASSET_IDS,
    TreasurySeedCounts,
    TreasurySeedCoverage,
)

_TREASURY_TYPE = AssetType.TESOURO_DIRETO.value


async def inspect_treasury_seed_state(
    db: AsyncSession,
) -> tuple[TreasurySeedCounts, TreasurySeedCoverage]:
    """Captura baseline, integridade e cobertura sem executar qualquer escrita."""

    treasury_assets = select(Asset.id).where(Asset.asset_type == _TREASURY_TYPE)

    assets = await db.scalar(
        select(func.count()).select_from(Asset).where(Asset.asset_type == _TREASURY_TYPE)
    )
    aliases = await db.scalar(
        select(func.count())
        .select_from(AssetAlias)
        .join(Asset, Asset.id == AssetAlias.asset_id)
        .where(Asset.asset_type == _TREASURY_TYPE)
    )
    prices = await db.scalar(
        select(func.count())
        .select_from(AssetPrice)
        .where(AssetPrice.asset_id.in_(treasury_assets))
    )
    orphan_prices = await db.scalar(
        select(func.count())
        .select_from(AssetPrice)
        .outerjoin(Asset, Asset.id == AssetPrice.asset_id)
        .where(Asset.id.is_(None))
    )

    duplicate_groups = (
        select(AssetPrice.asset_id, AssetPrice.timestamp)
        .where(AssetPrice.asset_id.in_(treasury_assets))
        .group_by(AssetPrice.asset_id, AssetPrice.timestamp)
        .having(func.count() > 1)
        .subquery()
    )
    duplicate_prices = await db.scalar(
        select(func.count()).select_from(duplicate_groups)
    )
    legacy_assets = await db.scalar(
        select(func.count())
        .select_from(Asset)
        .where(Asset.id.in_(LEGACY_TREASURY_ASSET_IDS))
    )
    legacy_prices = await db.scalar(
        select(func.count())
        .select_from(AssetPrice)
        .where(AssetPrice.asset_id.in_(LEGACY_TREASURY_ASSET_IDS))
    )

    coverage_row = (
        await db.execute(
            select(
                func.min(AssetPrice.timestamp),
                func.max(AssetPrice.timestamp),
                func.count(func.distinct(AssetPrice.asset_id)),
            ).where(AssetPrice.asset_id.in_(treasury_assets))
        )
    ).one()
    first_timestamp, last_timestamp, priced_assets = coverage_row

    counts = TreasurySeedCounts(
        assets=int(assets or 0),
        aliases=int(aliases or 0),
        prices=int(prices or 0),
        orphan_prices=int(orphan_prices or 0),
        duplicate_prices=int(duplicate_prices or 0),
        legacy_assets=int(legacy_assets or 0),
        legacy_prices=int(legacy_prices or 0),
    )
    coverage = TreasurySeedCoverage(
        first_price_date=(first_timestamp.date().isoformat() if first_timestamp else None),
        last_price_date=(last_timestamp.date().isoformat() if last_timestamp else None),
        priced_assets=int(priced_assets or 0),
    )
    return counts, coverage
