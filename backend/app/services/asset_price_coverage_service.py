"""Auditoria DB-only da cobertura historica de precos por ativo."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import DEDICATED_PRICE_TYPES, NO_QUOTE_TYPES
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.transaction import Transaction

_FRACTIONAL_RE = re.compile(r"^([A-Z0-9]{4,7})F$")
_FRACTIONAL_TYPES = {
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
}


class CoverageStatus(str, Enum):
    COMPLETE = "COMPLETE"
    MISSING = "MISSING"
    PARTIAL_START = "PARTIAL_START"
    STALE = "STALE"
    PARTIAL_BOTH = "PARTIAL_BOTH"
    MISSING_ASSET = "MISSING_ASSET"
    NO_MARKET_QUOTE = "NO_MARKET_QUOTE"
    DEDICATED_PROVIDER = "DEDICATED_PROVIDER"
    CANONICAL_ALIAS = "CANONICAL_ALIAS"


@dataclass(frozen=True)
class CoverageRange:
    date_from: date
    date_to: date
    reason: str


@dataclass(frozen=True)
class AssetPriceCoverage:
    ticker: str
    asset_type: str
    asset_id: int | None
    required_from: date | None
    required_to: date
    first_price_date: date | None
    last_price_date: date | None
    price_count: int
    status: CoverageStatus
    needs_sync: bool
    missing_ranges: tuple[CoverageRange, ...] = ()
    provider: str | None = None
    provider_symbol: str | None = None
    provider_status: str | None = None
    provider_last_sync_at: datetime | None = None
    provider_attempts: int = 0

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["missing_ranges"] = [
            {
                "date_from": item.date_from.isoformat(),
                "date_to": item.date_to.isoformat(),
                "reason": item.reason,
            }
            for item in self.missing_ranges
        ]
        return payload


def _as_asset_type(value: AssetType | str | None) -> AssetType:
    if isinstance(value, AssetType):
        return value
    return AssetType(str(value))


def _canonical_ticker(ticker: str, asset_type: AssetType) -> str | None:
    if asset_type not in _FRACTIONAL_TYPES:
        return None
    match = _FRACTIONAL_RE.fullmatch(ticker.upper())
    return match.group(1) if match else None


def classify_coverage(
    *,
    asset_type: AssetType,
    asset_exists: bool,
    required_from: date | None,
    required_to: date,
    first_price_date: date | None,
    last_price_date: date | None,
    grace_days: int = 5,
) -> CoverageStatus:
    if asset_type in NO_QUOTE_TYPES:
        return CoverageStatus.NO_MARKET_QUOTE
    if asset_type in DEDICATED_PRICE_TYPES:
        return CoverageStatus.DEDICATED_PROVIDER
    if not asset_exists:
        return CoverageStatus.MISSING_ASSET
    if first_price_date is None or last_price_date is None:
        return CoverageStatus.MISSING

    missing_start = required_from is not None and first_price_date > required_from + timedelta(days=grace_days)
    stale = last_price_date < required_to - timedelta(days=grace_days)
    if missing_start and stale:
        return CoverageStatus.PARTIAL_BOTH
    if missing_start:
        return CoverageStatus.PARTIAL_START
    if stale:
        return CoverageStatus.STALE
    return CoverageStatus.COMPLETE


def build_missing_ranges(
    *,
    status: CoverageStatus,
    required_from: date | None,
    required_to: date,
    first_price_date: date | None,
    last_price_date: date | None,
    provider_status: str | None = None,
    grace_days: int = 5,
) -> tuple[CoverageRange, ...]:
    if status in {
        CoverageStatus.COMPLETE,
        CoverageStatus.NO_MARKET_QUOTE,
        CoverageStatus.DEDICATED_PROVIDER,
        CoverageStatus.CANONICAL_ALIAS,
        CoverageStatus.MISSING_ASSET,
    }:
        return ()

    normalized_provider_status = str(provider_status or "").upper()
    history_unavailable = normalized_provider_status in {
        "HISTORY_UNAVAILABLE",
        "YAHOO_HISTORY_UNAVAILABLE",
    }
    start_exhausted = history_unavailable or normalized_provider_status in {
        "HISTORY_START_EXHAUSTED",
        "HISTORY_START_COMPLEMENT_UNAVAILABLE",
        "HISTORY_START_COMPLEMENT_GAPPED",
    }
    end_unavailable = history_unavailable or normalized_provider_status == "HISTORY_END_UNAVAILABLE"

    if history_unavailable:
        return ()

    ranges: list[CoverageRange] = []
    if status == CoverageStatus.MISSING:
        if required_from is not None and required_from <= required_to:
            ranges.append(CoverageRange(required_from, required_to, "missing_all"))
        return tuple(ranges)

    if status in {CoverageStatus.PARTIAL_START, CoverageStatus.PARTIAL_BOTH} and not start_exhausted:
        if required_from is not None and first_price_date is not None:
            end = min(required_to, first_price_date + timedelta(days=grace_days))
            if required_from <= end:
                ranges.append(CoverageRange(required_from, end, "missing_start"))

    if status in {CoverageStatus.STALE, CoverageStatus.PARTIAL_BOTH} and not end_unavailable:
        if last_price_date is not None:
            start = max(required_from or last_price_date, last_price_date - timedelta(days=grace_days))
            if start <= required_to:
                ranges.append(CoverageRange(start, required_to, "stale_end"))
    return tuple(ranges)


async def audit_asset_price_coverage(
    db: AsyncSession,
    *,
    required_to: date | None = None,
    full_history: bool = False,
    history_start: date | None = None,
) -> list[AssetPriceCoverage]:
    target = required_to or datetime.now(timezone.utc).date()
    global_start = history_start or date(1900, 1, 1)

    assets_result = await db.execute(select(Asset))
    assets = list(assets_result.scalars().all())
    assets_by_key = {(str(asset.ticker).upper(), str(asset.asset_type)): asset for asset in assets}

    tx_result = await db.execute(
        select(
            func.upper(Transaction.ticker).label("ticker"),
            Transaction.asset_type.label("asset_type"),
            func.min(Transaction.date).label("required_from"),
        ).group_by(func.upper(Transaction.ticker), Transaction.asset_type)
    )
    tx_requirements = {
        (str(row.ticker).upper(), str(row.asset_type)): row.required_from
        for row in tx_result.all()
    }

    price_result = await db.execute(
        select(
            AssetPrice.asset_id,
            func.min(AssetPrice.timestamp).label("first_ts"),
            func.max(AssetPrice.timestamp).label("last_ts"),
            func.count(AssetPrice.id).label("price_count"),
        ).group_by(AssetPrice.asset_id)
    )
    price_stats = {row.asset_id: row for row in price_result.all()}

    report: list[AssetPriceCoverage] = []
    for ticker, asset_type_raw in sorted(set(assets_by_key) | set(tx_requirements)):
        try:
            asset_type = _as_asset_type(asset_type_raw)
        except ValueError:
            asset_type = AssetType.OUTRO

        asset = assets_by_key.get((ticker, asset_type_raw))
        canonical_ticker = _canonical_ticker(ticker, asset_type)
        canonical_asset = assets_by_key.get((canonical_ticker, asset_type_raw)) if canonical_ticker else None
        pricing_asset = canonical_asset or asset
        stats = price_stats.get(pricing_asset.id) if pricing_asset is not None else None
        first_date = stats.first_ts.date() if stats and stats.first_ts else None
        last_date = stats.last_ts.date() if stats and stats.last_ts else None
        generic_full_history = asset_type not in NO_QUOTE_TYPES and asset_type not in DEDICATED_PRICE_TYPES
        required_from = global_start if full_history and generic_full_history else tx_requirements.get((ticker, asset_type_raw))
        provider_status = getattr(pricing_asset, "provider_status", None) if pricing_asset is not None else None

        if canonical_asset is not None and asset is not None and canonical_asset.id != asset.id:
            status = CoverageStatus.CANONICAL_ALIAS
            ranges: tuple[CoverageRange, ...] = ()
        else:
            status = classify_coverage(
                asset_type=asset_type,
                asset_exists=asset is not None,
                required_from=required_from,
                required_to=target,
                first_price_date=first_date,
                last_price_date=last_date,
            )
            ranges = build_missing_ranges(
                status=status,
                required_from=required_from,
                required_to=target,
                first_price_date=first_date,
                last_price_date=last_date,
                provider_status=provider_status,
            )

        report.append(
            AssetPriceCoverage(
                ticker=ticker,
                asset_type=asset_type.value,
                asset_id=asset.id if asset is not None else None,
                required_from=required_from,
                required_to=target,
                first_price_date=first_date,
                last_price_date=last_date,
                price_count=int(stats.price_count or 0) if stats else 0,
                status=status,
                needs_sync=bool(ranges),
                missing_ranges=ranges,
                provider=getattr(pricing_asset, "provider", None) if pricing_asset is not None else None,
                provider_symbol=(
                    canonical_ticker
                    or getattr(pricing_asset, "provider_symbol", None)
                    if pricing_asset is not None
                    else canonical_ticker
                ),
                provider_status=provider_status,
                provider_last_sync_at=(
                    getattr(pricing_asset, "provider_last_sync_at", None)
                    if pricing_asset is not None
                    else None
                ),
                provider_attempts=(
                    int(getattr(pricing_asset, "provider_attempts", 0) or 0)
                    if pricing_asset is not None
                    else 0
                ),
            )
        )
    return report


async def summarize_asset_price_coverage(
    db: AsyncSession,
    *,
    required_to: date | None = None,
    full_history: bool = False,
    history_start: date | None = None,
) -> dict:
    report = await audit_asset_price_coverage(
        db,
        required_to=required_to,
        full_history=full_history,
        history_start=history_start,
    )
    by_status: dict[str, int] = {}
    for item in report:
        by_status[item.status.value] = by_status.get(item.status.value, 0) + 1
    return {
        "total_assets": len(report),
        "needs_sync": sum(1 for item in report if item.needs_sync),
        "by_status": by_status,
        "assets": [item.to_dict() for item in report],
    }
