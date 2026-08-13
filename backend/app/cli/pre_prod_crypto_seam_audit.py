"""Audita, sem writes/providers, a costura BRAPI -> complemento CRIPTO persistido."""
from __future__ import annotations

import asyncio
import json
from datetime import timedelta

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

BRAPI_SOURCE = "brapi_v2_crypto_max"
COMPLEMENT_SOURCE = "yfinance_crypto_ptax_brl_max"


async def _run(*, tickers: set[str] | None = None) -> dict:
    normalized_tickers = (
        {str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()}
        if tickers is not None
        else None
    )
    stmt = (
        select(
            Asset.id.label("asset_id"),
            Asset.ticker,
            Asset.provider,
            Asset.provider_symbol,
            Asset.provider_status,
            Asset.provider_attempts,
            AssetPrice.source,
            func.count(AssetPrice.id).label("rows"),
            func.min(AssetPrice.timestamp).label("first_ts"),
            func.max(AssetPrice.timestamp).label("last_ts"),
        )
        .join(AssetPrice, AssetPrice.asset_id == Asset.id)
        .where(Asset.asset_type == AssetType.CRIPTO.value)
        .where(AssetPrice.source.in_((BRAPI_SOURCE, COMPLEMENT_SOURCE)))
    )
    if normalized_tickers is not None:
        stmt = stmt.where(func.upper(Asset.ticker).in_(normalized_tickers))
    stmt = stmt.group_by(
        Asset.id,
        Asset.ticker,
        Asset.provider,
        Asset.provider_symbol,
        Asset.provider_status,
        Asset.provider_attempts,
        AssetPrice.source,
    ).order_by(Asset.ticker.asc(), AssetPrice.source.asc())

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(stmt)).all()

    by_asset: dict[int, dict] = {}
    for row in rows:
        item = by_asset.setdefault(
            row.asset_id,
            {
                "asset_id": row.asset_id,
                "ticker": row.ticker,
                "provider": row.provider,
                "provider_symbol": row.provider_symbol,
                "provider_status": row.provider_status,
                "provider_attempts": int(row.provider_attempts or 0),
                "sources": {},
            },
        )
        item["sources"][row.source] = {
            "rows": int(row.rows or 0),
            "first_date": row.first_ts.date() if row.first_ts else None,
            "last_date": row.last_ts.date() if row.last_ts else None,
        }

    assets: list[dict] = []
    counts = {"continuous": 0, "gapped": 0, "no_seam": 0}
    for item in sorted(by_asset.values(), key=lambda value: value["ticker"]):
        brapi = item["sources"].get(BRAPI_SOURCE)
        complement = item["sources"].get(COMPLEMENT_SOURCE)
        expected_complement_end = None
        gap_days = None

        if brapi and complement and brapi["first_date"] and complement["last_date"]:
            expected_complement_end = brapi["first_date"] - timedelta(days=1)
            if complement["last_date"] >= expected_complement_end:
                seam_status = "continuous"
            else:
                seam_status = "gapped"
                gap_days = (expected_complement_end - complement["last_date"]).days
        else:
            seam_status = "no_seam"

        if item["provider_status"] == "HISTORY_START_COMPLEMENT_GAPPED":
            seam_status = "gapped"
            if brapi and complement and brapi["first_date"] and complement["last_date"]:
                expected_complement_end = brapi["first_date"] - timedelta(days=1)
                gap_days = max(0, (expected_complement_end - complement["last_date"]).days)

        counts[seam_status] += 1
        assets.append(
            {
                **item,
                "seam_status": seam_status,
                "expected_complement_end": expected_complement_end,
                "gap_days": gap_days,
            }
        )

    return {
        "read_only": True,
        "audited": len(assets),
        "by_seam_status": counts,
        "blocking_gaps": counts["gapped"],
        "assets": assets,
    }


def main() -> None:
    print(json.dumps(asyncio.run(_run()), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
