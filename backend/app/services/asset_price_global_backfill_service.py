"""Backfill global idempotente do historico de precos."""
from __future__ import annotations

import asyncio
import logging
from datetime import date

from app.core.database import AsyncSessionLocal
from app.services.asset_price_coverage_service import AssetPriceCoverage, audit_asset_price_coverage
from app.services.asset_price_gap_sync_service import AssetGapSyncResult, sync_asset_price_gaps
from app.services.price_sync_status_reconciler import reconcile_fii_end_unavailable

logger = logging.getLogger(__name__)

MAX_HISTORY_START = date(1900, 1, 1)
_GLOBAL_SYNC_CONCURRENCY = 4
_global_backfill_lock = asyncio.Lock()


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
            "audited": 0,
            "requested": 0,
            "inserted": 0,
            "errors": 0,
            "skipped": 0,
            "reconciled_fii_end": 0,
            "missing_assets": 0,
            "assets": [],
        }

    async with _global_backfill_lock:
        async with AsyncSessionLocal() as db:
            coverage = await audit_asset_price_coverage(
                db,
                required_to=required_to,
                full_history=True,
                history_start=history_start,
            )

        missing_assets = [item for item in coverage if item.asset_id is None]
        candidates = [item for item in coverage if item.needs_sync and item.asset_id is not None]
        results = await _sync_candidates(candidates, concurrency=concurrency)
        reconciliation = await reconcile_fii_end_unavailable(required_to=required_to)
        payload = {
            "running": False,
            "audited": len(coverage),
            "requested": len(results),
            "inserted": sum(item.rows_inserted for item in results),
            "errors": sum(1 for item in results if item.error),
            "skipped": sum(1 for item in results if item.skipped),
            "reconciled_fii_end": reconciliation["changed"],
            "missing_assets": len(missing_assets),
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
            "[global_price_backfill] audited=%d requested=%d inserted=%d errors=%d missing_assets=%d reconciled_fii_end=%d concurrency=%d",
            payload["audited"],
            payload["requested"],
            payload["inserted"],
            payload["errors"],
            payload["missing_assets"],
            payload["reconciled_fii_end"],
            concurrency,
        )
        return payload
