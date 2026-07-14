"""Sincronizacao idempotente das bordas ausentes do historico de precos.

O snapshot nunca chama este modulo. A sincronizacao e executada por onboarding, cron
ou comando administrativo. As sessoes de banco sao curtas: lemos a cobertura,
liberamos a conexao durante a chamada externa e abrimos outra sessao apenas para
persistir os dados obtidos.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.asset_types import INTL_TYPES, NO_QUOTE_TYPES
from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.asset_price_coverage_service import (
    AssetPriceCoverage,
    CoverageStatus,
    audit_asset_price_coverage,
)

logger = logging.getLogger(__name__)

_asset_locks: dict[int, asyncio.Lock] = {}
_asset_locks_guard = asyncio.Lock()
_GRACE_DAYS = 5


@dataclass(frozen=True)
class MissingPriceRange:
    date_from: date
    date_to: date
    reason: str


@dataclass(frozen=True)
class AssetGapSyncResult:
    asset_id: int | None
    ticker: str
    status_before: str
    requested_ranges: tuple[MissingPriceRange, ...]
    rows_received: int
    rows_inserted: int
    skipped: bool = False
    error: str | None = None


def build_missing_edge_ranges(coverage: AssetPriceCoverage) -> tuple[MissingPriceRange, ...]:
    """Calcula somente lacunas nas bordas conhecidas do historico.

    Lacunas internas serao tratadas em etapa posterior. Um pequeno overlap e
    proposital para cobrir feriados e permitir upsert idempotente.
    """
    if not coverage.needs_sync or coverage.asset_id is None:
        return ()
    if coverage.status in {CoverageStatus.NO_MARKET_QUOTE, CoverageStatus.MISSING_ASSET}:
        return ()

    required_from = coverage.required_from
    required_to = coverage.required_to
    ranges: list[MissingPriceRange] = []

    if coverage.status == CoverageStatus.MISSING:
        if required_from is not None and required_from <= required_to:
            ranges.append(MissingPriceRange(required_from, required_to, "missing_all"))
        return tuple(ranges)

    if coverage.status in {CoverageStatus.PARTIAL_START, CoverageStatus.PARTIAL_BOTH}:
        if required_from is not None and coverage.first_price_date is not None:
            end = min(required_to, coverage.first_price_date + timedelta(days=_GRACE_DAYS))
            if required_from <= end:
                ranges.append(MissingPriceRange(required_from, end, "missing_start"))

    if coverage.status in {CoverageStatus.STALE, CoverageStatus.PARTIAL_BOTH}:
        if coverage.last_price_date is not None:
            start = max(
                required_from or coverage.last_price_date,
                coverage.last_price_date - timedelta(days=_GRACE_DAYS),
            )
            if start <= required_to:
                ranges.append(MissingPriceRange(start, required_to, "stale_end"))

    return tuple(ranges)


async def _lock_for(asset_id: int) -> asyncio.Lock:
    async with _asset_locks_guard:
        return _asset_locks.setdefault(asset_id, asyncio.Lock())


async def _fetch_range(
    ticker: str,
    asset_type: AssetType,
    missing_range: MissingPriceRange,
) -> tuple[list[tuple[datetime, float]], str]:
    """Busca um intervalo sem manter conexao de banco aberta."""
    if asset_type in INTL_TYPES:
        from app.services.price_history_backfill_service import _fetch_intl_history

        days = max((date.today() - missing_range.date_from).days + 1, 2)
        rows, source = await _fetch_intl_history(ticker, asset_type, days)
    else:
        from app.services.price_history_backfill_service import _fetch_br_history

        rows, source = await _fetch_br_history(
            ticker,
            asset_type,
            missing_range.date_from.isoformat(),
            missing_range.date_to.isoformat(),
        )

    filtered: list[tuple[datetime, float]] = []
    for timestamp, close in rows:
        ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        if missing_range.date_from <= ts.date() <= missing_range.date_to and close and float(close) > 0:
            filtered.append((ts.astimezone(timezone.utc), float(close)))
    return filtered, source


async def _persist_rows(
    asset_id: int,
    rows: list[tuple[datetime, float, str]],
) -> int:
    if not rows:
        return 0

    inserted = 0
    async with AsyncSessionLocal() as db:
        for timestamp, close, source in rows:
            stmt = (
                pg_insert(AssetPrice)
                .values(
                    asset_id=asset_id,
                    timestamp=timestamp,
                    close=Decimal(str(round(close, 8))),
                    source=source or "gap_sync",
                )
                .on_conflict_do_nothing(constraint="uq_price_asset_timestamp")
                .returning(AssetPrice.id)
            )
            result = await db.execute(stmt)
            if result.scalar_one_or_none() is not None:
                inserted += 1

        latest = max(rows, key=lambda item: item[0])
        asset_result = await db.execute(select(Asset).where(Asset.id == asset_id))
        asset = asset_result.scalar_one_or_none()
        if asset is not None:
            last_saved = await db.execute(
                select(func.max(AssetPrice.timestamp)).where(AssetPrice.asset_id == asset_id)
            )
            last_ts = last_saved.scalar_one_or_none()
            if last_ts is not None and last_ts <= latest[0]:
                asset.last_price = Decimal(str(round(latest[1], 8)))
                asset.last_price_updated_at = latest[0]
        await db.commit()
    return inserted


async def sync_asset_price_gaps(coverage: AssetPriceCoverage) -> AssetGapSyncResult:
    """Sincroniza as lacunas de um ativo auditado, com lock por asset_id."""
    ranges = build_missing_edge_ranges(coverage)
    if coverage.asset_id is None or not ranges:
        return AssetGapSyncResult(
            asset_id=coverage.asset_id,
            ticker=coverage.ticker,
            status_before=coverage.status.value,
            requested_ranges=ranges,
            rows_received=0,
            rows_inserted=0,
            skipped=True,
        )

    try:
        asset_type = AssetType(coverage.asset_type)
    except ValueError as exc:
        return AssetGapSyncResult(
            asset_id=coverage.asset_id,
            ticker=coverage.ticker,
            status_before=coverage.status.value,
            requested_ranges=ranges,
            rows_received=0,
            rows_inserted=0,
            skipped=True,
            error=str(exc),
        )

    if asset_type in NO_QUOTE_TYPES:
        return AssetGapSyncResult(
            asset_id=coverage.asset_id,
            ticker=coverage.ticker,
            status_before=coverage.status.value,
            requested_ranges=(),
            rows_received=0,
            rows_inserted=0,
            skipped=True,
        )

    lock = await _lock_for(coverage.asset_id)
    async with lock:
        collected: list[tuple[datetime, float, str]] = []
        try:
            for missing_range in ranges:
                rows, source = await _fetch_range(coverage.ticker, asset_type, missing_range)
                collected.extend((timestamp, close, source) for timestamp, close in rows)
            inserted = await _persist_rows(coverage.asset_id, collected)
            logger.info(
                "[price_gap_sync] %s ranges=%s received=%d inserted=%d",
                coverage.ticker,
                len(ranges),
                len(collected),
                inserted,
            )
            return AssetGapSyncResult(
                asset_id=coverage.asset_id,
                ticker=coverage.ticker,
                status_before=coverage.status.value,
                requested_ranges=ranges,
                rows_received=len(collected),
                rows_inserted=inserted,
            )
        except Exception as exc:
            logger.exception("[price_gap_sync] falha para %s", coverage.ticker)
            return AssetGapSyncResult(
                asset_id=coverage.asset_id,
                ticker=coverage.ticker,
                status_before=coverage.status.value,
                requested_ranges=ranges,
                rows_received=len(collected),
                rows_inserted=0,
                error=str(exc),
            )


async def sync_all_asset_price_gaps(*, required_to: date | None = None) -> dict:
    """Audita todos os ativos e sincroniza apenas os que possuem bordas ausentes."""
    async with AsyncSessionLocal() as db:
        coverage = await audit_asset_price_coverage(db, required_to=required_to)

    results: list[AssetGapSyncResult] = []
    for item in coverage:
        if item.needs_sync:
            results.append(await sync_asset_price_gaps(item))

    return {
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
                        "date_from": r.date_from.isoformat(),
                        "date_to": r.date_to.isoformat(),
                        "reason": r.reason,
                    }
                    for r in item.requested_ranges
                ],
                "rows_received": item.rows_received,
                "rows_inserted": item.rows_inserted,
                "skipped": item.skipped,
                "error": item.error,
            }
            for item in results
        ],
    }
