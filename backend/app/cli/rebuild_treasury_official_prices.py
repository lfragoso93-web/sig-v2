"""Reconstrói apenas os preços oficiais do Tesouro em ativos canônicos ativos."""
from __future__ import annotations

import asyncio
import json

from sqlalchemy import delete, func, select

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.treasury_official_history_service import rebuild_official_treasury_history

_OFFICIAL_SOURCES = ("tesouro_transparente", "brapi_treasury")


async def _main() -> None:
    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(Asset.id).where(
                Asset.asset_type == AssetType.TESOURO_DIRETO.value,
                func.coalesce(Asset.provider_status, "") != "NOT_APPLICABLE",
            )
        )
        active_ids = [int(asset_id) for asset_id in rows.scalars().all()]
        removed = 0
        if active_ids:
            result = await db.execute(
                delete(AssetPrice)
                .where(
                    AssetPrice.asset_id.in_(active_ids),
                    AssetPrice.source.in_(_OFFICIAL_SOURCES),
                )
                .returning(AssetPrice.id)
            )
            removed = len(result.scalars().all())
            await db.commit()

    rebuilt = await rebuild_official_treasury_history()
    print(
        json.dumps(
            {
                "removed_official_prices": removed,
                "active_assets": len(active_ids),
                "rebuild": rebuilt,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    asyncio.run(_main())
