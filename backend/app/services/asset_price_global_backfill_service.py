"""Backfill global idempotente do historico de precos."""
from __future__ import annotations

import asyncio
import logging
from datetime import date

from sqlalchemy import select

from app.core.asset_types import INTL_TYPES
from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction
from app.services.asset_price_coverage_service import AssetPriceCoverage, audit_asset_price_coverage
from app.services.asset_price_gap_sync_service import AssetGapSyncResult, sync_asset_price_gaps

logger = logging.getLogger(__name__)

MAX_HISTORY_START = date(1900, 1, 1)
_GLOBAL_SYNC_CONCURRENCY = 4
_global_backfill_lock = asyncio.Lock()


def _currency_for(asset_type: AssetType) -> str:
    return "USD" if asset_type in INTL_TYPES else "BRL"


async def ensure_transaction_assets_in_catalog() -> dict:
    created = 0
    invalid = 0
    async with AsyncSessionLocal() as db:
        tx_result = await db.execute(select(Transaction.ticker, Transaction.asset_type).distinct())
        transaction_assets = tx_result.all()
        asset_result = await db.execute(select(Asset.ticker, Asset.asset_type))
        known = {(str(row.ticker).upper(), str(row.asset_type)) for row in asset_result.all()}

        for row in transaction_assets:
            ticker = str(row.ticker or "").upper().strip()
            asset_type_raw = str(row.asset_type or "")
            if not ticker:
                invalid += 1
                continue
            try:
                asset_type = AssetType(asset_type_raw)
            except ValueError:
                logger.warning("[global_price_backfill] tipo invalido: %s/%s", ticker, asset_type_raw)
                invalid += 1
                continue
            key = (ticker, asset_type.value)
            if key in known:
                continue
            db.add(
                Asset(
                    ticker=ticker,
                    name=ticker,
                    asset_type=asset_type.value,
                    currency=_currency_for(asset_type),
                    provider_symbol=ticker,
                    provider_status="PENDING",
                )
            )
            known.add(key)
            created += 1
        await db.commit()
    return {"created": created, "invalid": invalid}


async def _sync_candidates(
    candidates: list[AssetPriceCoverage],
    *,
    concurrency: int,
) -> list[AssetGapSyncResult]:
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _run(item: AssetPriceCoverage) -> AssetGapSyncResult:
        async with semaphore:
            return await sync_asset_price_gaps(item)

    return list(await asyncio.gather(*[_run(item) for item in candidates]))


async def run_global_asset_price_backfill(
    *,
    required_to: date | None = None,
    history_start: date = MAX_HISTORY_START,
    concurrency: int = _GLOBAL_SYNC_CONCURRENCY,
) -> dict:
    if _global_backfill_lock.locked():
        logger.info("[global_price_backfill] ja em execucao — ignorando nova chamada")
        return {
            "running": True,
            "catalog_created": 0,
            "audited": 0,
            "requested": 0,
            "inserted": 0,
            "errors": 0,
            "skipped": 0,
            "assets": [],
        }

    async with _global_backfill_lock:
        catalog = await ensure_transaction_assets_in_catalog()
        async with AsyncSessionLocal() as db:
            coverage = await audit_asset_price_coverage(
                db,
                required_to=required_to,
                full_history=True,
                history_start=history_start,
            )

        candidates = [item for item in coverage if item.needs_sync]
        results = await _sync_candidates(candidates, concurrency=concurrency)
        payload = {
            "running": False,
            "catalog_created": catalog["created"],
            "catalog_invalid": catalog["invalid"],
            "audited": len(coverage),
            "requested": len(results),
            "inserted": sum(item.rows_inserted for item in results),
            "errors": sum(1 for item in results if item.error),
            "skipped": sum(1 for item in results if item.skipped),
            "assets": [
                {
                    "asset_id": item.asset_id,
                    "ticker": item.ticker,
                    "status_before": item.status_before,
                    "ranges": [
                        {
                            "date_from": interval.date_from.isoformat(),
                            "date_to": interval.date_to.isoformat(),
                            "reason": interval.reason,
                        }
                        for interval in item.requested_ranges
                    ],
                    "rows_received": item.rows_received,
                    "rows_inserted": item.rows_inserted,
                    "skipped": item.skipped,
                    "error": item.error,
                }
                for item in results
            ],
        }
        logger.info(
            "[global_price_backfill] audited=%d requested=%d inserted=%d errors=%d concurrency=%d",
            payload["audited"],
            payload["requested"],
            payload["inserted"],
            payload["errors"],
            concurrency,
        )
        return payload
