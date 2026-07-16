"""Reconcilia estados persistentes após o gap sync.

O coletor pode receber linhas já existentes sem alcançar a data requerida. Para
FIIs consultados no dia, essa situação é registrada como cauda indisponível para
não repetir a mesma janela em cada full rebuild.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.services.asset_price_coverage_service import audit_asset_price_coverage


async def reconcile_fii_end_unavailable(*, required_to: date | None = None) -> dict[str, int]:
    target = required_to or datetime.now(timezone.utc).date()
    changed = 0
    inspected = 0

    async with AsyncSessionLocal() as db:
        coverage = await audit_asset_price_coverage(db, required_to=target)
        candidates = [
            item
            for item in coverage
            if item.asset_id is not None
            and item.asset_type == AssetType.FII.value
            and any(price_range.reason == "stale_end" for price_range in item.missing_ranges)
            and item.provider_last_sync_at is not None
            and item.provider_last_sync_at.date() == target
            and str(item.provider_status or "").upper() == "OK"
        ]
        inspected = len(candidates)
        if not candidates:
            return {"inspected": 0, "changed": 0}

        ids = [item.asset_id for item in candidates if item.asset_id is not None]
        result = await db.execute(select(Asset).where(Asset.id.in_(ids)))
        for asset in result.scalars().all():
            asset.provider_status = "HISTORY_END_UNAVAILABLE"
            asset.provider_last_error = None
            changed += 1
        await db.commit()

    return {"inspected": inspected, "changed": changed}
