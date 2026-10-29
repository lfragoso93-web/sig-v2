"""Read-only ORM adapter for canonical portfolio dividend entitlements."""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.fx_rate import FxRate
from app.models.transaction import Transaction
from app.services.canonical_dividend_entitlement import (
    DividendEntitlement,
    DividendEvent,
    PositionMovement,
    calculate_dividend_entitlement,
)

_TYPE_ALIASES: dict[str, str] = {
    "ETF": "ETF_NACIONAL",
    "ETF_BR": "ETF_NACIONAL",
    "ETF_INT": "ETF_INTERNACIONAL",
    "ACAO_NACIONAL": "ACAO",
    "ACOES": "ACAO",
    "STOCKS": "STOCK",
    "TESOURO": "TESOURO_DIRETO",
    "CRIPTOMOEDA": "CRIPTO",
}


def normalize_asset_type(val: object) -> str:
    raw = getattr(val, "value", val)
    s = str(raw or "").strip().upper()
    return _TYPE_ALIASES.get(s, s)


_normalize_asset_type = normalize_asset_type


@dataclass(frozen=True, slots=True)
class PortfolioDividendEntitlement:
    ticker: str
    asset_type: str
    event: DividendEvent
    entitlement: DividendEntitlement
    approved_on: date | None
    gross_value_per_unit: Decimal | None
    factor: Decimal | None
    complete_factor: Decimal | None
    isin_code: str | None
    asset_issued: str | None
    related_to: str | None
    remarks: str | None


async def load_portfolio_dividend_entitlements(
    db: AsyncSession,
    portfolio_id: int,
    *,
    ex_date_from: date | None = None,
    ex_date_to: date | None = None,
) -> list[PortfolioDividendEntitlement]:
    """Load global events and derive rights without persisting portfolio rows."""
    events_stmt = (
        select(AssetDividend, Asset)
        .join(Asset, AssetDividend.asset_id == Asset.id)
        .join(
            Transaction,
            and_(
                func.upper(func.trim(Transaction.ticker)) == func.upper(func.trim(Asset.ticker)),
                or_(
                    Transaction.asset_type == Asset.asset_type,
                    and_(Transaction.asset_type == "ETF", Asset.asset_type == "ETF_NACIONAL"),
                    and_(Transaction.asset_type == "ETF_NACIONAL", Asset.asset_type == "ETF"),
                    and_(Transaction.asset_type == "ETF_INT", Asset.asset_type == "ETF_INTERNACIONAL"),
                    and_(Transaction.asset_type == "ETF_INTERNACIONAL", Asset.asset_type == "ETF_INT"),
                    and_(Transaction.asset_type == "STOCKS", Asset.asset_type == "STOCK"),
                    and_(Transaction.asset_type == "STOCK", Asset.asset_type == "STOCKS"),
                ),
            ),
        )
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
        .order_by(AssetDividend.ex_date, AssetDividend.id)
    )
    if ex_date_from is not None:
        events_stmt = events_stmt.where(AssetDividend.ex_date >= ex_date_from)
    if ex_date_to is not None:
        events_stmt = events_stmt.where(AssetDividend.ex_date <= ex_date_to)

    event_rows = (await db.execute(events_stmt)).all()
    if not event_rows:
        return []

    movements_stmt = (
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date, Transaction.id)
    )
    transactions = (await db.execute(movements_stmt)).scalars().all()

    usd_ref_dates = [
        asset_dividend.payment_date or asset_dividend.ex_date
        for asset_dividend, asset in event_rows
        if str(asset.currency or "").strip().upper() == "USD"
    ]
    fx_dates: list[date] = []
    fx_rates: list[Decimal] = []
    if usd_ref_dates:
        fx_dates, fx_rates = await load_usd_brl_rates(db, max(usd_ref_dates))

    movements_by_asset: dict[tuple[str, str], list[PositionMovement]] = {}
    for transaction in transactions:
        t_ticker = str(transaction.ticker or "").strip().upper()
        t_type = _normalize_asset_type(transaction.asset_type)
        movements_by_asset.setdefault((t_ticker, t_type), []).append(
            PositionMovement(
                transaction_date=transaction.date,
                operation=_enum_value(transaction.operation),
                quantity=Decimal(str(transaction.quantity)),
            )
        )

    results: list[PortfolioDividendEntitlement] = []
    for asset_dividend, asset in event_rows:
        currency = str(asset.currency or "").strip().upper()
        if not currency:
            raise ValueError(f"asset {asset.ticker} has no currency")
        value_per_unit = Decimal(str(asset_dividend.value_per_unit))
        gross_value_per_unit = _optional_decimal(
            asset_dividend.gross_value_per_unit
        )
        if currency == "USD":
            ref_date = asset_dividend.payment_date or asset_dividend.ex_date
            fx_rate = lookup_fx_rate_on_or_before(fx_dates, fx_rates, ref_date)
            if fx_rate is not None:
                value_per_unit = (value_per_unit * fx_rate).quantize(
                    Decimal("0.00000001"),
                    rounding=ROUND_HALF_UP,
                )
                if gross_value_per_unit is not None:
                    gross_value_per_unit = (
                        gross_value_per_unit * fx_rate
                    ).quantize(
                        Decimal("0.00000001"),
                        rounding=ROUND_HALF_UP,
                    )
                currency = "BRL"

        event = DividendEvent(
            event_id=asset_dividend.id,
            record_date=asset_dividend.record_date,
            ex_date=asset_dividend.ex_date,
            payment_date=asset_dividend.payment_date,
            event_type=_enum_value(asset_dividend.dividend_type),
            value_per_unit=value_per_unit,
            currency=currency,
        )
        norm_ticker = str(asset.ticker or "").strip().upper()
        norm_type = _normalize_asset_type(asset.asset_type)
        key = (norm_ticker, norm_type)
        movements = movements_by_asset.get(key, ())
        if not movements:
            movements = movements_by_asset.get((norm_ticker, str(asset.asset_type).strip().upper()), ())

        results.append(
            PortfolioDividendEntitlement(
                ticker=asset.ticker,
                asset_type=_enum_value(asset.asset_type),
                event=event,
                entitlement=calculate_dividend_entitlement(
                    event,
                    movements,
                ),
                approved_on=asset_dividend.approved_on,
                gross_value_per_unit=gross_value_per_unit,
                factor=_optional_decimal(asset_dividend.factor),
                complete_factor=_optional_decimal(
                    asset_dividend.complete_factor
                ),
                isin_code=asset_dividend.isin_code,
                asset_issued=asset_dividend.asset_issued,
                related_to=asset_dividend.related_to,
                remarks=asset_dividend.remarks,
            )
        )
    return results


async def load_usd_brl_rates(
    db: AsyncSession,
    max_date: date,
) -> tuple[list[date], list[Decimal]]:
    """Load persisted USD-BRL rates up to max_date in a single batch query."""
    fx_stmt = (
        select(FxRate.rate_date, FxRate.rate)
        .where(FxRate.pair == "USD-BRL", FxRate.rate_date <= max_date)
        .order_by(FxRate.rate_date.asc(), FxRate.id.asc())
    )
    fx_rows = (await db.execute(fx_stmt)).all()
    by_date: dict[date, Decimal] = {}
    for row in fx_rows:
        if hasattr(row, "rate_date") and hasattr(row, "rate"):
            r_date, r_val = row.rate_date, row.rate
        else:
            r_date, r_val = row[0], row[1]
        by_date[r_date] = Decimal(str(r_val))
    sorted_dates = sorted(by_date.keys())
    sorted_rates = [by_date[d] for d in sorted_dates]
    return sorted_dates, sorted_rates


def lookup_fx_rate_on_or_before(
    rate_dates: list[date],
    rates: list[Decimal],
    ref_date: date,
) -> Decimal | None:
    """Resolve the latest persisted FX rate on or before ref_date."""
    idx = bisect_right(rate_dates, ref_date) - 1
    if idx < 0:
        return None
    return rates[idx]


def _enum_value(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw)


def _optional_decimal(value: object | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))
