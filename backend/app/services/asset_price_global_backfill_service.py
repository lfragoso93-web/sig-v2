"""Backfill global idempotente do historico de precos."""
from __future__ import annotations

import asyncio
import logging
from datetime import date

from app.core.database import AsyncSessionLocal
from app.models.asset import AssetType
from app.services.asset_price_coverage_service import AssetPriceCoverage, audit_asset_price_coverage
from app.services.asset_price_gap_sync_service import AssetGapSyncResult, sync_asset_price_gaps

logger = logging.getLogger(__name__)

MAX_HISTORY_START = date(1900, 1, 1)
_GLOBAL_SYNC_CONCURRENCY = 4
_global_backfill_lock = asyncio.Lock()

_DEDICATED_BOOTSTRAP_PRICE_TYPES = {
    AssetType.ACAO.value,
    AssetType.FII.value,
    AssetType.ETF_NACIONAL.value,
    AssetType.BDR.value,
    AssetType.TESOURO_DIRETO.value,
}


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
    asset_types: set[str] | None = None,
    tickers: set[str] | None = None,
) -> dict:
    normalized_asset_types = (
        {str(asset_type).upper() for asset_type in asset_types}
        if asset_types is not None
        else None
    )
    normalized_tickers = (
        {str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()}
        if tickers is not None
        else None
    )
    if _global_backfill_lock.locked():
        logger.info("[global_price_backfill] ja em execucao — ignorando nova chamada")
        return {
            "running": True,
            "audited": 0,
            "requested": 0,
            "inserted": 0,
            "errors": 0,
            "skipped": 0,
            "missing_assets": 0,
            "dedicated_provider_assets": 0,
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

        scoped_coverage = [
            item
            for item in coverage
            if (normalized_asset_types is None or item.asset_type in normalized_asset_types)
            and (normalized_tickers is None or item.ticker.upper() in normalized_tickers)
        ]
        missing_assets = [item for item in scoped_coverage if item.asset_id is None]
        dedicated_provider_assets = [
            item
            for item in scoped_coverage
            if item.asset_id is not None
            and item.asset_type in _DEDICATED_BOOTSTRAP_PRICE_TYPES
        ]
        candidates = [
            item
            for item in scoped_coverage
            if item.needs_sync
            and item.asset_id is not None
            and item.asset_type not in _DEDICATED_BOOTSTRAP_PRICE_TYPES
        ]
        results = await _sync_candidates(candidates, concurrency=concurrency)
        payload = {
            "running": False,
            "audited": len(scoped_coverage),
            "requested": len(results),
            "inserted": sum(item.rows_inserted for item in results),
            "errors": sum(1 for item in results if item.error),
            "skipped": sum(1 for item in results if item.skipped),
            "missing_assets": len(missing_assets),
            "dedicated_provider_assets": len(dedicated_provider_assets),
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
            "[global_price_backfill] audited=%d requested=%d inserted=%d errors=%d missing_assets=%d dedicated_provider_assets=%d concurrency=%d",
            payload["audited"],
            payload["requested"],
            payload["inserted"],
            payload["errors"],
            payload["missing_assets"],
            payload["dedicated_provider_assets"],
            concurrency,
        )
        return payload
