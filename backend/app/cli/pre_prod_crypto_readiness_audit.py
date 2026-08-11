"""Audita readiness do histórico CRIPTO suportado sem providers e sem writes."""
from __future__ import annotations

import asyncio
import json

from sqlalchemy import func, select

from app.cli import pre_prod_crypto_seam_audit, pre_prod_crypto_shallow_history_audit
from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.crypto_supported_universe_service import (
    fetch_supported_crypto_tickers,
)

BLOCKING_STATUSES = (
    "HISTORY_START_TRUNCATED",
    "HISTORY_START_COMPLEMENT_GAPPED",
    "HISTORY_START_SHALLOW",
    "HISTORY_START_SHALLOW_UNAVAILABLE",
)


async def _run() -> dict:
    supported_tickers = await fetch_supported_crypto_tickers()

    async with AsyncSessionLocal() as db:
        total_crypto = int(
            (await db.execute(
                select(func.count(Asset.id))
                .where(Asset.asset_type == AssetType.CRIPTO.value)
                .where(func.upper(Asset.ticker).in_(supported_tickers))
            )).scalar_one()
            or 0
        )

        no_history = int(
            (await db.execute(
                select(func.count(Asset.id))
                .where(Asset.asset_type == AssetType.CRIPTO.value)
                .where(func.upper(Asset.ticker).in_(supported_tickers))
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
                .where(func.upper(Asset.ticker).in_(supported_tickers))
                .where(Asset.provider_status.in_(BLOCKING_STATUSES))
                .group_by(Asset.provider_status)
            )
        ).all()
        by_blocking_status = {str(status): int(count or 0) for status, count in blocking_rows}

        blocking_asset_rows = (
            await db.execute(
                select(
                    Asset.ticker,
                    Asset.provider,
                    Asset.provider_symbol,
                    Asset.provider_status,
                    Asset.provider_attempts,
                )
                .where(Asset.asset_type == AssetType.CRIPTO.value)
                .where(func.upper(Asset.ticker).in_(supported_tickers))
                .where(Asset.provider_status.in_(BLOCKING_STATUSES))
                .order_by(Asset.provider_status, Asset.ticker)
            )
        ).all()
        blocking_assets = [
            {
                "ticker": str(row.ticker),
                "provider": row.provider,
                "provider_symbol": row.provider_symbol,
                "provider_status": row.provider_status,
                "provider_attempts": int(row.provider_attempts or 0),
            }
            for row in blocking_asset_rows
        ]

        duplicate_groups = (
            select(AssetPrice.asset_id, AssetPrice.timestamp)
            .join(Asset, Asset.id == AssetPrice.asset_id)
            .where(Asset.asset_type == AssetType.CRIPTO.value)
            .where(func.upper(Asset.ticker).in_(supported_tickers))
            .group_by(AssetPrice.asset_id, AssetPrice.timestamp)
            .having(func.count(AssetPrice.id) > 1)
            .subquery()
        )
        duplicates = int(
            (await db.execute(select(func.count()).select_from(duplicate_groups))).scalar_one()
            or 0
        )

    seam = await pre_prod_crypto_seam_audit._run(tickers=supported_tickers)
    shallow = await pre_prod_crypto_shallow_history_audit._run(tickers=supported_tickers)
    blocking_statuses = sum(by_blocking_status.values())
    shallow_histories = int(shallow["shallow_histories"])
    ready = (
        total_crypto == len(supported_tickers)
        and no_history == 0
        and duplicates == 0
        and blocking_statuses == 0
        and int(seam["blocking_gaps"]) == 0
        and shallow_histories == 0
    )

    return {
        "read_only": True,
        "universe_policy": "top_100_market_cap_coingecko_intersect_brapi",
        "supported_universe_size": len(supported_tickers),
        "crypto_price_history_ready": ready,
        "total_crypto_assets": total_crypto,
        "no_history": no_history,
        "duplicates": duplicates,
        "blocking_statuses": by_blocking_status,
        "blocking_assets": blocking_assets,
        "blocking_seams": int(seam["blocking_gaps"]),
        "shallow_histories": shallow_histories,
        "shallow_history_audit": shallow,
        "seam_audit": seam,
    }


def main() -> None:
    print(json.dumps(asyncio.run(_run()), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
