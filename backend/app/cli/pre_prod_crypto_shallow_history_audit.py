"""Audita historicos CRIPTO excessivamente rasos sem providers e sem writes."""
from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

SHALLOW_MAX_ROWS = 7
SHALLOW_MAX_AGE_DAYS = 30
NON_RETRY_SHALLOW_STATUSES = (
    "HISTORY_START_SHALLOW_VERIFIED",
    "HISTORY_START_SHALLOW_UNAVAILABLE",
)


async def _run(*, required_to: date | None = None, tickers: set[str] | None = None) -> dict:
    target = required_to or date.today()
    cutoff = target - timedelta(days=SHALLOW_MAX_AGE_DAYS)
    normalized_tickers = (
        {str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()}
        if tickers is not None
        else None
    )

    async with AsyncSessionLocal() as db:
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

        stmt = (
            select(
                Asset.id,
                Asset.ticker,
                Asset.provider,
                Asset.provider_symbol,
                Asset.provider_status,
                stats.c.rows,
                stats.c.first_ts,
                stats.c.last_ts,
            )
            .join(stats, stats.c.asset_id == Asset.id)
            .where(Asset.asset_type == AssetType.CRIPTO.value)
            .where(stats.c.rows <= SHALLOW_MAX_ROWS)
            .where(func.date(stats.c.first_ts) >= cutoff)
            .where(
                (Asset.provider_status.is_(None))
                | (~Asset.provider_status.in_(NON_RETRY_SHALLOW_STATUSES))
            )
        )
        if normalized_tickers is not None:
            stmt = stmt.where(func.upper(Asset.ticker).in_(normalized_tickers))
        stmt = stmt.order_by(Asset.ticker)

        rows = (await db.execute(stmt)).all()

    assets = [
        {
            "asset_id": int(row.id),
            "ticker": str(row.ticker),
            "provider": row.provider,
            "provider_symbol": row.provider_symbol,
            "provider_status": row.provider_status,
            "rows": int(row.rows or 0),
            "first_date": row.first_ts.date().isoformat() if row.first_ts else None,
            "last_date": row.last_ts.date().isoformat() if row.last_ts else None,
        }
        for row in rows
    ]

    return {
        "read_only": True,
        "required_to": target.isoformat(),
        "shallow_max_rows": SHALLOW_MAX_ROWS,
        "shallow_max_age_days": SHALLOW_MAX_AGE_DAYS,
        "shallow_histories": len(assets),
        "assets": assets,
    }


def main() -> None:
    print(json.dumps(asyncio.run(_run()), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
