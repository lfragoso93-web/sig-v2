"""Backfill guardado de metadados tipados do Tesouro Direto."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.treasury_instrument import TreasuryInstrument

_SYNTHETIC_PROVIDER = "synthetic-certification"


async def _schema_ready(db: AsyncSession) -> bool:
    result = await db.execute(
        text("SELECT to_regclass('public.treasury_instruments')")
    )
    return result.scalar_one_or_none() is not None


async def backfill_treasury_instruments(
    db: AsyncSession,
    *,
    dry_run: bool = True,
) -> dict[str, object]:
    """Planeja ou insere apenas nomes já persistidos em ``assets``."""
    if not await _schema_ready(db):
        return {
            "schema_version": "treasury-instrument-backfill.v1",
            "dry_run": dry_run,
            "schema_ready": False,
            "candidate_count": 0,
            "candidate_asset_ids": [],
            "conflict_count": 0,
            "conflicts": [],
            "database_writes_executed": 0,
        }

    result = await db.execute(
        select(Asset)
        .outerjoin(
            TreasuryInstrument,
            TreasuryInstrument.asset_id == Asset.id,
        )
        .where(
            Asset.asset_type == AssetType.TESOURO_DIRETO.value,
            TreasuryInstrument.asset_id.is_(None),
            Asset.name.is_not(None),
            func.length(func.trim(Asset.name)) > 0,
            func.coalesce(Asset.provider, "") != _SYNTHETIC_PROVIDER,
        )
        .order_by(Asset.id)
    )
    assets = list(result.scalars().all())
    candidate_ids = [int(asset.id) for asset in assets]
    assets_by_normalized_ticker: dict[str, list[int]] = defaultdict(list)
    for asset in assets:
        normalized_ticker = str(asset.ticker or "").strip().lower()
        if normalized_ticker:
            assets_by_normalized_ticker[normalized_ticker].append(int(asset.id))
    conflicts = [
        {
            "normalized_ticker": ticker,
            "asset_ids": asset_ids,
        }
        for ticker, asset_ids in sorted(assets_by_normalized_ticker.items())
        if len(asset_ids) > 1
    ]
    report: dict[str, object] = {
        "schema_version": "treasury-instrument-backfill.v1",
        "dry_run": dry_run,
        "schema_ready": True,
        "candidate_count": len(assets),
        "candidate_asset_ids": candidate_ids,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "database_writes_executed": 0,
    }
    if dry_run or not assets or conflicts:
        return report

    instruments = [
        TreasuryInstrument(
            asset_id=int(asset.id),
            commercial_name=str(asset.name).strip(),
            metadata_source="assets.name",
        )
        for asset in assets
    ]
    try:
        db.add_all(instruments)
        await db.flush()
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return {
        **report,
        "dry_run": False,
        "database_writes_executed": len(instruments),
    }
