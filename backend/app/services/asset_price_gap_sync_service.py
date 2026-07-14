"""Sincronizacao idempotente das lacunas do historico de precos."""
from __future__ import annotations

import asyncio
import logging
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
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

# NUMERIC(18, 8) aceita valores absolutos menores que 10^10. Um preço unitário
# próximo desse limite é, na prática, dado corrompido de ajuste/grupamento.
MAX_REASONABLE_UNIT_PRICE = 100_000_000.0
_FRACTIONAL_TICKER_RE = re.compile(r"^([A-Z0-9]{4,7})F$")
_FRACTIONAL_TYPES = {
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
}


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
    return tuple(
        MissingPriceRange(item.date_from, item.date_to, item.reason)
        for item in coverage.missing_ranges
    )


def _default_provider(asset_type: AssetType) -> str:
    return "alpha_vantage" if asset_type in INTL_TYPES else "brapi"


def normalize_provider_symbol(ticker: str, asset_type: AssetType) -> str:
    """Normaliza o símbolo do provedor sem alterar o ticker contábil.

    O mercado fracionário brasileiro usa a mesma referência de preço do lote
    padrão. Ex.: WEGE3F -> WEGE3, TAEE11F -> TAEE11.
    """
    normalized = ticker.upper().strip()
    if asset_type in _FRACTIONAL_TYPES:
        match = _FRACTIONAL_TICKER_RE.fullmatch(normalized)
        if match:
            return match.group(1)
    return normalized


def _default_provider_symbol(ticker: str, asset_type: AssetType) -> str:
    # Cripto e Tesouro terao roteamento dedicado em bloco posterior.
    return normalize_provider_symbol(ticker, asset_type)


def _is_valid_price(value: object) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(numeric) and 0 < numeric < MAX_REASONABLE_UNIT_PRICE


async def _lock_for(asset_id: int) -> asyncio.Lock:
    async with _asset_locks_guard:
        return _asset_locks.setdefault(asset_id, asyncio.Lock())


async def _fetch_range(
    ticker: str,
    asset_type: AssetType,
    missing_range: MissingPriceRange,
) -> tuple[list[tuple[datetime, float]], str]:
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
    rejected = 0
    for timestamp, close in rows:
        ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        if not (missing_range.date_from <= ts.date() <= missing_range.date_to):
            continue
        if not _is_valid_price(close):
            rejected += 1
            logger.warning(
                "[price_gap_sync] preço rejeitado ticker=%s data=%s close=%r source=%s",
                ticker,
                ts.date(),
                close,
                source,
            )
            continue
        filtered.append((ts.astimezone(timezone.utc), float(close)))

    if rejected:
        logger.warning(
            "[price_gap_sync] ticker=%s rejeitados=%d por validação de preço",
            ticker,
            rejected,
        )
    return filtered, source


async def _persist_result(
    *,
    coverage: AssetPriceCoverage,
    rows: list[tuple[datetime, float, str]],
    provider: str,
    provider_symbol: str,
    start_exhausted: bool,
    error: str | None = None,
) -> int:
    if coverage.asset_id is None:
        return 0

    inserted = 0
    async with AsyncSessionLocal() as db:
        asset_result = await db.execute(select(Asset).where(Asset.id == coverage.asset_id))
        asset = asset_result.scalar_one_or_none()
        if asset is None:
            return 0

        for timestamp, close, source in rows:
            if not _is_valid_price(close):
                continue
            stmt = (
                pg_insert(AssetPrice)
                .values(
                    asset_id=coverage.asset_id,
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

        now = datetime.now(timezone.utc)
        asset.provider = provider
        asset.provider_symbol = provider_symbol
        asset.provider_last_sync_at = now
        asset.provider_attempts = int(asset.provider_attempts or 0) + 1
        asset.provider_last_error = error
        if error:
            asset.provider_status = "FAILED"
        elif start_exhausted:
            asset.provider_status = "HISTORY_START_EXHAUSTED"
        else:
            asset.provider_status = "OK"

        if rows:
            valid_rows = [item for item in rows if _is_valid_price(item[1])]
            if valid_rows:
                latest = max(valid_rows, key=lambda item: item[0])
                last_saved = await db.execute(
                    select(func.max(AssetPrice.timestamp)).where(AssetPrice.asset_id == coverage.asset_id)
                )
                last_ts = last_saved.scalar_one_or_none()
                if last_ts is not None and last_ts <= latest[0]:
                    asset.last_price = Decimal(str(round(latest[1], 8)))
                    asset.last_price_updated_at = latest[0]

        await db.commit()
    return inserted


async def sync_asset_price_gaps(coverage: AssetPriceCoverage) -> AssetGapSyncResult:
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
            coverage.asset_id,
            coverage.ticker,
            coverage.status.value,
            ranges,
            0,
            0,
            True,
            str(exc),
        )

    if asset_type in NO_QUOTE_TYPES:
        return AssetGapSyncResult(
            coverage.asset_id,
            coverage.ticker,
            coverage.status.value,
            (),
            0,
            0,
            True,
        )

    provider = coverage.provider or _default_provider(asset_type)
    provider_symbol = normalize_provider_symbol(
        coverage.provider_symbol or coverage.ticker,
        asset_type,
    )
    lock = await _lock_for(coverage.asset_id)

    async with lock:
        collected: list[tuple[datetime, float, str]] = []
        start_requested = any(item.reason in {"missing_start", "missing_all"} for item in ranges)
        try:
            for missing_range in ranges:
                rows, source = await _fetch_range(provider_symbol, asset_type, missing_range)
                collected.extend((timestamp, close, source) for timestamp, close in rows)

            inserted = await _persist_result(
                coverage=coverage,
                rows=collected,
                provider=provider,
                provider_symbol=provider_symbol,
                start_exhausted=start_requested and inserted_count_will_be_zero(collected, coverage),
            )
            if start_requested and inserted == 0:
                await _persist_result(
                    coverage=coverage,
                    rows=[],
                    provider=provider,
                    provider_symbol=provider_symbol,
                    start_exhausted=True,
                )

            logger.info(
                "[price_gap_sync] %s ranges=%s received=%d inserted=%d provider=%s symbol=%s",
                coverage.ticker,
                len(ranges),
                len(collected),
                inserted,
                provider,
                provider_symbol,
            )
            return AssetGapSyncResult(
                coverage.asset_id,
                coverage.ticker,
                coverage.status.value,
                ranges,
                len(collected),
                inserted,
            )
        except Exception as exc:
            await _persist_result(
                coverage=coverage,
                rows=[],
                provider=provider,
                provider_symbol=provider_symbol,
                start_exhausted=False,
                error=str(exc),
            )
            logger.exception("[price_gap_sync] falha para %s", coverage.ticker)
            return AssetGapSyncResult(
                coverage.asset_id,
                coverage.ticker,
                coverage.status.value,
                ranges,
                len(collected),
                0,
                False,
                str(exc),
            )


def inserted_count_will_be_zero(
    rows: list[tuple[datetime, float, str]],
    coverage: AssetPriceCoverage,
) -> bool:
    """Heuristica conservadora; a confirmação definitiva ocorre após o upsert."""
    return not rows and coverage.price_count > 0


async def sync_all_asset_price_gaps(*, required_to: date | None = None, concurrency: int = 4) -> dict:
    async with AsyncSessionLocal() as db:
        coverage = await audit_asset_price_coverage(db, required_to=required_to)

    candidates = [item for item in coverage if item.needs_sync]
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _run(item: AssetPriceCoverage) -> AssetGapSyncResult:
        async with semaphore:
            return await sync_asset_price_gaps(item)

    results = await asyncio.gather(*[_run(item) for item in candidates])
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
