"""Sincronizacao idempotente das lacunas do historico de precos."""
from __future__ import annotations

import asyncio
import logging
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.asset_types import INTL_TYPES, NO_QUOTE_TYPES, yf_ticker
from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.services.asset_price_coverage_service import (
    AssetPriceCoverage,
    audit_asset_price_coverage,
    build_missing_ranges,
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
    "BITCOIN": "BTC-BRL",
    "BTC": "BTC-BRL",
    "ETHEREUM": "ETH-BRL",
    "ETH": "ETH-BRL",
    "CARDANO": "ADA-BRL",
    "ADA": "ADA-BRL",
    "SOLANA": "SOL-BRL",
    "SOL": "SOL-BRL",
    "RIPPLE": "XRP-BRL",
    "XRP": "XRP-BRL",
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
    source_ranges = coverage.missing_ranges
    if not source_ranges:
        source_ranges = build_missing_ranges(
            status=coverage.status,
            required_from=coverage.required_from,
            required_to=coverage.required_to,
            first_price_date=coverage.first_price_date,
            last_price_date=coverage.last_price_date,
            provider_status=coverage.provider_status,
        )
    return tuple(
        MissingPriceRange(item.date_from, item.date_to, item.reason)
        for item in source_ranges
    )


def _default_provider(asset_type: AssetType) -> str:
    if asset_type == AssetType.CRIPTO:
        return "brapi"
    return "alpha_vantage" if asset_type in INTL_TYPES else "brapi"


def normalize_provider_symbol(ticker: str, asset_type: AssetType) -> str:
    normalized = ticker.upper().strip()
    if asset_type == AssetType.CRIPTO:
        return _CRYPTO_SYMBOLS.get(
            normalized,
            normalized if normalized.endswith("-BRL") else f"{normalized}-BRL",
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


async def _fetch_crypto_history(ticker: str) -> tuple[list[tuple[datetime, float]], str, str]:
    from app.integrations.brapi_crypto_history import fetch_brapi_crypto_history

    try:
        rows = await fetch_brapi_crypto_history(
            ticker,
            currency="BRL",
            range_="max",
            interval="1d",
        )
    except Exception as exc:
        logger.info(
            "[price_gap_sync] brapi crypto indisponivel ticker=%s; usando yahoo: %s",
            ticker,
            exc,
        )
        rows = []

    if rows:
        return rows, "brapi_v2_crypto_max", "brapi"

    fallback = await _fetch_yf_max(ticker, AssetType.CRIPTO)
    return fallback, "yfinance_crypto_max", "yfinance"


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
        rows, source, effective_provider = await _fetch_crypto_history(ticker)
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

    if filtered and asset_type == AssetType.CRIPTO and initial_history:
        terminal_status = "HISTORY_START_EXHAUSTED"
    elif not filtered:
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
    asset_id: int,
    rows: list[tuple[datetime, float]],
    *,
    source: str,
    provider: str,
    provider_symbol: str,
    terminal_status: str | None,
    error: str | None = None,
) -> int:
    async with AsyncSessionLocal() as db:
        inserted = 0
        for timestamp, close in rows:
            stmt = (
                pg_insert(AssetPrice)
                .values(
                    asset_id=asset_id,
                    timestamp=timestamp,
                    close=Decimal(str(round(close, 8))),
                    source=source,
                )
                .on_conflict_do_nothing(constraint="uq_price_asset_timestamp")
                .returning(AssetPrice.id)
            )
            persisted = await db.execute(stmt)
            if persisted.scalar_one_or_none() is not None:
                inserted += 1

        update_values = {
            "provider": provider,
            "provider_symbol": provider_symbol,
            "provider_status": terminal_status or "ACTIVE",
            "provider_last_sync_at": datetime.now(timezone.utc),
            "provider_last_error": error,
            "provider_attempts": func.coalesce(Asset.provider_attempts, 0) + 1,
        }
        await db.execute(
            Asset.__table__.update().where(Asset.id == asset_id).values(**update_values)
        )
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

    asset_type = AssetType(str(coverage.asset_type))
    if asset_type in NO_QUOTE_TYPES:
        return AssetGapSyncResult(
            asset_id=coverage.asset_id,
            ticker=coverage.ticker,
            status_before=coverage.status.value,
            requested_ranges=ranges,
            rows_received=0,
            rows_inserted=0,
            skipped=True,
        )

    provider_symbol = normalize_provider_symbol(coverage.ticker, asset_type)
    lock = await _lock_for(coverage.asset_id)
    async with lock:
        total_received = 0
        total_inserted = 0
        errors: list[str] = []
        for missing_range in ranges:
            try:
                rows, source, terminal_status, provider = await _fetch_range(
                    provider_symbol,
                    asset_type,
                    missing_range,
                )
                total_received += len(rows)
                total_inserted += await _persist_result(
                    coverage.asset_id,
                    rows,
                    source=source,
                    provider=provider,
                    provider_symbol=provider_symbol,
                    terminal_status=terminal_status,
                )
            except Exception as exc:
                logger.exception(
                    "[price_gap_sync] falha ticker=%s intervalo=%s..%s",
                    coverage.ticker,
                    missing_range.date_from,
                    missing_range.date_to,
                )
                errors.append(str(exc))

        return AssetGapSyncResult(
            asset_id=coverage.asset_id,
            ticker=coverage.ticker,
            status_before=coverage.status.value,
            requested_ranges=ranges,
            rows_received=total_received,
            rows_inserted=total_inserted,
            error="; ".join(errors) if errors else None,
        )


async def sync_all_asset_price_gaps(
    *,
    required_to: date | None = None,
    full_history: bool = False,
    history_start: date | None = None,
    concurrency: int = 4,
) -> list[AssetGapSyncResult]:
    async with AsyncSessionLocal() as db:
        coverage = await audit_asset_price_coverage(
            db,
            required_to=required_to,
            full_history=full_history,
            history_start=history_start,
        )

    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _run(item: AssetPriceCoverage) -> AssetGapSyncResult:
        async with semaphore:
            return await sync_asset_price_gaps(item)

    return await asyncio.gather(*(_run(item) for item in coverage))
