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

from app.core.asset_types import INTL_TYPES, NO_QUOTE_TYPES, yf_ticker
from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.asset_price_coverage_service import (
    AssetPriceCoverage,
    audit_asset_price_coverage,
)

logger = logging.getLogger(__name__)

_asset_locks: dict[int, asyncio.Lock] = {}
_asset_locks_guard = asyncio.Lock()

MAX_REASONABLE_UNIT_PRICE = 100_000_000.0
_FRACTIONAL_TICKER_RE = re.compile(r"^([A-Z0-9]{4,7})F$")
_FRACTIONAL_TYPES = {
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
}
_INITIAL_RANGE_REASONS = {"missing_start", "missing_all"}
_CRYPTO_SYMBOLS = {
    "BITCOIN": "BTC-USD",
    "BTC": "BTC-USD",
    "ETHEREUM": "ETH-USD",
    "ETH": "ETH-USD",
    "CARDANO": "ADA-USD",
    "ADA": "ADA-USD",
    "SOLANA": "SOL-USD",
    "SOL": "SOL-USD",
    "RIPPLE": "XRP-USD",
    "XRP": "XRP-USD",
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
    if asset_type == AssetType.CRIPTO:
        return "yfinance"
    return "alpha_vantage" if asset_type in INTL_TYPES else "brapi"


def normalize_provider_symbol(ticker: str, asset_type: AssetType) -> str:
    normalized = ticker.upper().strip()
    if asset_type == AssetType.CRIPTO:
        return _CRYPTO_SYMBOLS.get(
            normalized,
            normalized if normalized.endswith("-USD") else f"{normalized}-USD",
        )
    if asset_type in _FRACTIONAL_TYPES:
        match = _FRACTIONAL_TICKER_RE.fullmatch(normalized)
        if match:
            return match.group(1)
    return normalized


def _is_valid_price(value: object) -> bool:
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(numeric) and 0 < numeric < MAX_REASONABLE_UNIT_PRICE


async def _lock_for(asset_id: int) -> asyncio.Lock:
    async with _asset_locks_guard:
        return _asset_locks.setdefault(asset_id, asyncio.Lock())


def _fetch_yf_max_sync(symbol: str) -> list[tuple[datetime, float]]:
    import yfinance as yf

    try:
        history = yf.Ticker(symbol).history(period="max", interval="1d", auto_adjust=True)
        if history.empty:
            return []
        rows: list[tuple[datetime, float]] = []
        for timestamp, row in history.iterrows():
            close = row.get("Close")
            if close is None:
                continue
            ts = timestamp.to_pydatetime()
            ts = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
            rows.append((ts, float(close)))
        return rows
    except Exception as exc:
        logger.info("[price_gap_sync] yahoo max indisponivel symbol=%s: %s", symbol, exc)
        return []


async def _fetch_yf_max(symbol: str, asset_type: AssetType) -> list[tuple[datetime, float]]:
    from app.services.price_history_service import _run_yf_with_throttle

    resolved = symbol if asset_type == AssetType.CRIPTO else yf_ticker(symbol, asset_type)
    return await _run_yf_with_throttle(_fetch_yf_max_sync, resolved)


def _empty_status(missing_range: MissingPriceRange) -> str:
    if missing_range.reason == "missing_all":
        return "HISTORY_UNAVAILABLE"
    if missing_range.reason == "missing_start":
        return "HISTORY_START_EXHAUSTED"
    return "HISTORY_END_UNAVAILABLE"


async def _fetch_range(
    ticker: str,
    asset_type: AssetType,
    missing_range: MissingPriceRange,
) -> tuple[list[tuple[datetime, float]], str, str | None, str]:
    initial_history = missing_range.reason in _INITIAL_RANGE_REASONS
    rows: list[tuple[datetime, float]] = []
    source = ""
    terminal_status: str | None = None
    effective_provider = _default_provider(asset_type)

    if asset_type == AssetType.CRIPTO:
        rows = await _fetch_yf_max(ticker, asset_type)
        source = "yfinance_crypto_max"
        effective_provider = "yfinance"
    elif asset_type in INTL_TYPES:
        if initial_history:
            rows = await _fetch_yf_max(ticker, asset_type)
            source = "yfinance_period_max"
            effective_provider = "yfinance"
        else:
            from app.services.price_history_backfill_service import _fetch_intl_history

            days = max((date.today() - missing_range.date_from).days + 1, 2)
            rows, source = await _fetch_intl_history(ticker, asset_type, days)
            effective_provider = "yfinance" if "yfinance" in str(source).lower() else "alpha_vantage"
    else:
        from app.integrations.brapi import fetch_fii_historical_v2, fetch_stocks_historical_v2

        effective_provider = "brapi"
        if asset_type == AssetType.FII:
            rows = await fetch_fii_historical_v2(
                ticker=ticker,
                date_from=missing_range.date_from.isoformat(),
                date_to=missing_range.date_to.isoformat(),
            )
            source = "brapi_v2_fii"
        elif initial_history:
            rows = await fetch_stocks_historical_v2(ticker=ticker, range_="max")
            source = "brapi_v2_stocks_max"
        else:
            rows = await fetch_stocks_historical_v2(
                ticker=ticker,
                date_from=missing_range.date_from.isoformat(),
                date_to=missing_range.date_to.isoformat(),
            )
            source = "brapi_v2_stocks"

    filtered: list[tuple[datetime, float]] = []
    rejected = 0
    for timestamp, close in rows:
        ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        if not (missing_range.date_from <= ts.date() <= missing_range.date_to):
            continue
        if not _is_valid_price(close):
            rejected += 1
            continue
        filtered.append((ts.astimezone(timezone.utc), float(close)))

    if not filtered:
        terminal_status = _empty_status(missing_range)
    if rejected:
        logger.warning(
            "[price_gap_sync] precos rejeitados ticker=%s quantidade=%d source=%s intervalo=%s..%s",
            ticker,
            rejected,
            source,
            missing_range.date_from,
            missing_range.date_to,
        )
    return filtered, source, terminal_status, effective_provider


async def _persist_result(
    *,
    coverage: AssetPriceCoverage,
    rows: list[tuple[datetime, float, str]],
    provider: str,
    provider_symbol: str,
    status: str,
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

        asset.provider = provider
        asset.provider_symbol = provider_symbol
        asset.provider_last_sync_at = datetime.now(timezone.utc)
        asset.provider_attempts = int(asset.provider_attempts or 0) + 1
        asset.provider_last_error = error
        asset.provider_status = "FAILED" if error else status

        if rows:
            latest = max(rows, key=lambda item: item[0])
            last_saved = await db.execute(
                select(func.max(AssetPrice.timestamp)).where(AssetPrice.asset_id == coverage.asset_id)
            )
            last_ts = last_saved.scalar_one_or_none()
            if last_ts is not None and last_ts <= latest[0]:
                asset.last_price = Decimal(str(round(latest[1], 8)))
                asset.last_price_updated_at = latest[0]

        await db.commit()
    return inserted


def _merge_terminal_statuses(statuses: list[str]) -> str:
    values = set(statuses)
    if "HISTORY_UNAVAILABLE" in values:
        return "HISTORY_UNAVAILABLE"
    if "HISTORY_START_EXHAUSTED" in values and "HISTORY_END_UNAVAILABLE" in values:
        return "HISTORY_UNAVAILABLE"
    if "HISTORY_END_UNAVAILABLE" in values:
        return "HISTORY_END_UNAVAILABLE"
    if "HISTORY_START_EXHAUSTED" in values:
        return "HISTORY_START_EXHAUSTED"
    return "OK"


async def sync_asset_price_gaps(coverage: AssetPriceCoverage) -> AssetGapSyncResult:
    ranges = build_missing_edge_ranges(coverage)
    if coverage.asset_id is None or not ranges:
        return AssetGapSyncResult(
            coverage.asset_id,
            coverage.ticker,
            coverage.status.value,
            ranges,
            0,
            0,
            True,
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

    provider_symbol = normalize_provider_symbol(
        coverage.provider_symbol or coverage.ticker,
        asset_type,
    )
    lock = await _lock_for(coverage.asset_id)

    async with lock:
        collected: list[tuple[datetime, float, str]] = []
        terminal_statuses: list[str] = []
        effective_providers: list[str] = []
        try:
            for missing_range in ranges:
                rows, source, terminal_status, effective_provider = await _fetch_range(
                    provider_symbol,
                    asset_type,
                    missing_range,
                )
                collected.extend((timestamp, close, source) for timestamp, close in rows)
                effective_providers.append(effective_provider)
                if terminal_status:
                    terminal_statuses.append(terminal_status)

            provider = effective_providers[-1] if effective_providers else _default_provider(asset_type)
            final_status = _merge_terminal_statuses(terminal_statuses)
            inserted = await _persist_result(
                coverage=coverage,
                rows=collected,
                provider=provider,
                provider_symbol=provider_symbol,
                status=final_status,
            )

            initial_requested = any(item.reason in _INITIAL_RANGE_REASONS for item in ranges)
            if initial_requested and collected and inserted == 0 and final_status == "OK":
                final_status = "HISTORY_START_EXHAUSTED"
                await _persist_result(
                    coverage=coverage,
                    rows=[],
                    provider=provider,
                    provider_symbol=provider_symbol,
                    status=final_status,
                )

            logger.info(
                "[price_gap_sync] %s ranges=%s received=%d inserted=%d provider=%s symbol=%s status=%s",
                coverage.ticker,
                len(ranges),
                len(collected),
                inserted,
                provider,
                provider_symbol,
                final_status,
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
            provider = effective_providers[-1] if effective_providers else _default_provider(asset_type)
            await _persist_result(
                coverage=coverage,
                rows=[],
                provider=provider,
                provider_symbol=provider_symbol,
                status="FAILED",
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


async def sync_all_asset_price_gaps(
    *,
    required_to: date | None = None,
    concurrency: int = 4,
) -> dict:
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
