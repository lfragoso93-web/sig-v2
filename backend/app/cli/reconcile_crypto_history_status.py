"""Reconcilia metadata do canário CRIPTO sem consultar providers externos."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date
from typing import cast

from sqlalchemy import CursorResult, func, select, update

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

EXPECTED_ROWS = 1000
EXPECTED_FIRST_DATE = date(2023, 11, 15)
EXPECTED_LAST_DATE = date(2026, 8, 10)
EXPECTED_SOURCE = "brapi_v2_crypto_max"
EXPECTED_PROVIDER_ATTEMPTS = 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcilia HISTORY_START_EXHAUSTED para HISTORY_START_TRUNCATED "
            "somente quando a evidência persistida do canário BRAPI for exata."
        )
    )
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--apply", action="store_true")
    return parser


def _normalize_tickers(values: list[str]) -> set[str]:
    return {str(value).strip().upper() for value in values if str(value).strip()}


async def _inspect_asset(db, ticker: str) -> dict:
    asset_result = await db.execute(
        select(Asset).where(
            Asset.asset_type == AssetType.CRIPTO.value,
            func.upper(Asset.ticker) == ticker,
        )
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        return {"ticker": ticker, "eligible": False, "reasons": ["asset_not_found"]}

    stats_result = await db.execute(
        select(
            func.count(AssetPrice.id),
            func.min(AssetPrice.timestamp),
            func.max(AssetPrice.timestamp),
        ).where(AssetPrice.asset_id == asset.id)
    )
    row_count, first_ts, last_ts = stats_result.one()

    source_result = await db.execute(
        select(AssetPrice.source, func.count(AssetPrice.id))
        .where(AssetPrice.asset_id == asset.id)
        .group_by(AssetPrice.source)
    )
    sources = {str(source): int(count) for source, count in source_result.all()}

    first_date = first_ts.date() if first_ts is not None else None
    last_date = last_ts.date() if last_ts is not None else None
    reasons: list[str] = []

    if str(asset.currency or "").upper() != "BRL":
        reasons.append("currency_not_brl")
    if str(asset.provider or "").lower() != "brapi":
        reasons.append("provider_not_brapi")
    if str(asset.provider_symbol or "").upper() != f"{ticker}-BRL":
        reasons.append("provider_symbol_mismatch")
    if str(asset.provider_status or "") != "HISTORY_START_EXHAUSTED":
        reasons.append("provider_status_not_legacy_exhausted")
    if int(asset.provider_attempts or 0) != EXPECTED_PROVIDER_ATTEMPTS:
        reasons.append("provider_attempts_mismatch")
    if int(row_count or 0) != EXPECTED_ROWS:
        reasons.append("row_count_mismatch")
    if first_date != EXPECTED_FIRST_DATE:
        reasons.append("first_date_mismatch")
    if last_date != EXPECTED_LAST_DATE:
        reasons.append("last_date_mismatch")
    if sources != {EXPECTED_SOURCE: EXPECTED_ROWS}:
        reasons.append("source_distribution_mismatch")

    return {
        "asset_id": asset.id,
        "ticker": ticker,
        "eligible": not reasons,
        "reasons": reasons,
        "provider_status": asset.provider_status,
        "provider_attempts": int(asset.provider_attempts or 0),
        "price_rows": int(row_count or 0),
        "first_date": first_date,
        "last_date": last_date,
        "sources": sources,
    }


async def _run(args: argparse.Namespace) -> dict:
    tickers = _normalize_tickers(args.ticker)
    async with AsyncSessionLocal() as db:
        assets = [await _inspect_asset(db, ticker) for ticker in sorted(tickers)]
        eligible = [item for item in assets if item["eligible"]]

        updated = 0
        if args.apply:
            for item in eligible:
                statement = (
                    update(Asset)
                    .where(
                        Asset.id == item["asset_id"],
                        Asset.provider_status == "HISTORY_START_EXHAUSTED",
                        Asset.provider_attempts == EXPECTED_PROVIDER_ATTEMPTS,
                    )
                    .values(provider_status="HISTORY_START_TRUNCATED")
                )
                result = cast(CursorResult, await db.execute(statement))
                updated += int(result.rowcount or 0)
            await db.commit()

    return {
        "apply": bool(args.apply),
        "requested": len(tickers),
        "eligible": len(eligible),
        "updated": updated,
        "assets": assets,
    }


def main() -> None:
    args = _parser().parse_args()
    result = asyncio.run(_run(args))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
