"""Seleciona de forma deterministica um lote DB-only de CRIPTO sem historico."""
from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seleciona CRIPTO sem historico para o proximo lote operacional."
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--after-ticker", default=None)
    return parser


def _normalize_limit(value: int) -> int:
    return min(MAX_LIMIT, max(1, int(value)))


def _normalize_after_ticker(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


async def _run(limit: int, after_ticker: str | None) -> dict:
    price_count = func.count(AssetPrice.id)
    stmt = (
        select(
            Asset.id,
            Asset.ticker,
            Asset.name,
            Asset.currency,
            Asset.provider,
            Asset.provider_symbol,
            Asset.provider_status,
            Asset.provider_attempts,
            price_count.label("price_rows"),
        )
        .outerjoin(AssetPrice, AssetPrice.asset_id == Asset.id)
        .where(Asset.asset_type == AssetType.CRIPTO.value)
        .group_by(
            Asset.id,
            Asset.ticker,
            Asset.name,
            Asset.currency,
            Asset.provider,
            Asset.provider_symbol,
            Asset.provider_status,
            Asset.provider_attempts,
        )
        .having(price_count == 0)
        .order_by(Asset.ticker.asc(), Asset.id.asc())
        .limit(limit)
    )
    if after_ticker is not None:
        stmt = stmt.where(Asset.ticker > after_ticker)

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(stmt)).all()

    assets = [
        {
            "asset_id": row.id,
            "ticker": row.ticker,
            "name": row.name,
            "currency": row.currency,
            "provider": row.provider,
            "provider_symbol": row.provider_symbol,
            "provider_status": row.provider_status,
            "provider_attempts": row.provider_attempts,
            "price_rows": int(row.price_rows or 0),
        }
        for row in rows
    ]
    return {
        "read_only": True,
        "limit": limit,
        "after_ticker": after_ticker,
        "selected": len(assets),
        "assets": assets,
    }


def main() -> None:
    args = _parser().parse_args()
    limit = _normalize_limit(args.limit)
    after_ticker = _normalize_after_ticker(args.after_ticker)
    result = asyncio.run(_run(limit, after_ticker))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
