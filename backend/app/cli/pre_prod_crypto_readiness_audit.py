"""Audita readiness do histórico CRIPTO sem providers e sem writes."""
from __future__ import annotations

import asyncio
import json

from sqlalchemy import func, select

from app.cli import pre_prod_crypto_seam_audit
from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

BLOCKING_STATUSES = (
    "HISTORY_START_TRUNCATED",
    "HISTORY_START_COMPLEMENT_GAPPED",
)


async def _run() -> dict:
    async with AsyncSessionLocal() as db:
        total_crypto = int(
            (await db.execute(
                select(func.count(Asset.id)).where(Asset.asset_type == AssetType.CRIPTO.value)
            )).scalar_one()
            or 0
        )

        no_history = int(
            (await db.execute(
                select(func.count(Asset.id))
                .where(Asset.asset_type == AssetType.CRIPTO.value)
                .where(
                    ~select(AssetPrice.id)
                    .where(AssetPrice.asset_id == Asset.id)
                    .exists()
                )
            )).scalar_one()
            or 0
        )

        blocking_rows = (
            await db.execute(
                select(Asset.provider_status, func.count(Asset.id))
                .where(Asset.asset_type == AssetType.CRIPTO.value)
                .where(Asset.provider_status.in_(BLOCKING_STATUSES))
                .group_by(Asset.provider_status)
            )
        ).all()
        by_blocking_status = {str(status): int(count or 0) for status, count in blocking_rows}

        duplicate_groups = (
            select(AssetPrice.asset_id, AssetPrice.timestamp)
            .join(Asset, Asset.id == AssetPrice.asset_id)
            .where(Asset.asset_type == AssetType.CRIPTO.value)
            .group_by(AssetPrice.asset_id, AssetPrice.timestamp)
            .having(func.count(AssetPrice.id) > 1)
            .subquery()
        )
        duplicates = int(
            (await db.execute(select(func.count()).select_from(duplicate_groups))).scalar_one()
            or 0
        )

    seam = await pre_prod_crypto_seam_audit._run()
    blocking_statuses = sum(by_blocking_status.values())
    ready = (
        no_history == 0
        and duplicates == 0
        and blocking_statuses == 0
        and int(seam["blocking_gaps"]) == 0
    )

    return {
        "read_only": True,
        "crypto_price_history_ready": ready,
        "total_crypto_assets": total_crypto,
        "no_history": no_history,
        "duplicates": duplicates,
        "blocking_statuses": by_blocking_status,
        "blocking_seams": int(seam["blocking_gaps"]),
        "seam_audit": seam,
    }


def main() -> None:
    print(json.dumps(asyncio.run(_run()), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
