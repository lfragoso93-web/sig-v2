"""Audita, sem writes/providers, indisponibilidades residuais de histórico CRIPTO."""
from __future__ import annotations

import asyncio
import json

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

TARGET_STATUSES = (
    "HISTORY_START_SHALLOW_UNAVAILABLE",
    "HISTORY_UNAVAILABLE",
)


async def _run() -> dict:
    stats = (
        select(
            AssetPrice.asset_id.label("asset_id"),
            func.count(AssetPrice.id).label("rows"),
            func.min(AssetPrice.timestamp).label("first_ts"),
            func.max(AssetPrice.timestamp).label("last_ts"),
        )
        .group_by(AssetPrice.asset_id)
        .subquery()
    )

    source_rows_stmt = (
        select(
            AssetPrice.asset_id,
            AssetPrice.source,
            func.count(AssetPrice.id).label("rows"),
            func.min(AssetPrice.timestamp).label("first_ts"),
            func.max(AssetPrice.timestamp).label("last_ts"),
        )
        .join(Asset, Asset.id == AssetPrice.asset_id)
        .where(Asset.asset_type == AssetType.CRIPTO.value)
        .where(Asset.provider_status.in_(TARGET_STATUSES))
        .group_by(AssetPrice.asset_id, AssetPrice.source)
        .order_by(AssetPrice.asset_id, AssetPrice.source)
    )

    assets_stmt = (
        select(
            Asset.id,
            Asset.ticker,
            Asset.provider,
            Asset.provider_symbol,
            Asset.provider_status,
            Asset.provider_attempts,
            Asset.provider_last_error,
            stats.c.rows,
            stats.c.first_ts,
            stats.c.last_ts,
        )
        .outerjoin(stats, stats.c.asset_id == Asset.id)
        .where(Asset.asset_type == AssetType.CRIPTO.value)
        .where(Asset.provider_status.in_(TARGET_STATUSES))
        .order_by(Asset.ticker)
    )

    async with AsyncSessionLocal() as db:
        asset_rows = (await db.execute(assets_stmt)).all()
        source_rows = (await db.execute(source_rows_stmt)).all()

    sources_by_asset: dict[int, list[dict]] = {}
    for row in source_rows:
        sources_by_asset.setdefault(int(row.asset_id), []).append(
            {
                "source": str(row.source),
                "rows": int(row.rows or 0),
                "first_date": row.first_ts.date() if row.first_ts else None,
                "last_date": row.last_ts.date() if row.last_ts else None,
            }
        )

    by_status = {status: 0 for status in TARGET_STATUSES}
    assets: list[dict] = []
    for row in asset_rows:
        status = str(row.provider_status)
        by_status[status] += 1
        rows = int(row.rows or 0)
        assets.append(
            {
                "asset_id": int(row.id),
                "ticker": str(row.ticker),
                "provider": row.provider,
                "provider_symbol": row.provider_symbol,
                "provider_status": status,
                "provider_attempts": int(row.provider_attempts or 0),
                "provider_last_error": row.provider_last_error,
                "rows": rows,
                "first_history_date": row.first_ts.date() if row.first_ts else None,
                "last_history_date": row.last_ts.date() if row.last_ts else None,
                "sources": sources_by_asset.get(int(row.id), []),
                "availability_class": "no_history" if rows == 0 else "shallow_history",
                "cause_classification": "requires_external_evidence",
            }
        )

    return {
        "read_only": True,
        "provider_calls": False,
        "target_statuses": list(TARGET_STATUSES),
        "audited": len(assets),
        "by_status": by_status,
        "assets": assets,
    }


def main() -> None:
    print(json.dumps(asyncio.run(_run()), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
