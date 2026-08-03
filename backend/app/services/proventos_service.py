"""Canonical read-only projections for the public Proventos API."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import asset_type_label
from app.models.dividend_enums import DividendStatus, DividendType
from app.services.canonical_dividend_entitlement import EntitlementReason
from app.services.canonical_dividend_entitlement_reader import (
    PortfolioDividendEntitlement,
    load_portfolio_dividend_entitlements,
)

_MONEY_STEP = Decimal("0.01")


def _enum_text(value: object) -> str:
    return str(getattr(value, "value", value)).upper()


def _payment_status(
    item: PortfolioDividendEntitlement,
    *,
    today: date,
) -> DividendStatus:
    payment_date = item.event.payment_date
    if payment_date is not None and payment_date <= today:
        return DividendStatus.RECEBIDO
    return DividendStatus.A_RECEBER


def _event_year(item: PortfolioDividendEntitlement) -> int:
    return (item.event.payment_date or item.event.ex_date).year


def _matches(
    item: PortfolioDividendEntitlement,
    *,
    today: date,
    status: DividendStatus | None,
    year: int | None,
    asset_type: str | None,
    dividend_type: DividendType | None,
) -> bool:
    return (
        (status is None or _payment_status(item, today=today) is status)
        and (year is None or _event_year(item) == year)
        and (asset_type is None or item.asset_type.upper() == asset_type.upper())
        and (
            dividend_type is None
            or item.event.event_type.upper() == dividend_type.value.upper()
        )
    )


async def _load_filtered(
    db: AsyncSession,
    portfolio_id: int,
    *,
    status: DividendStatus | None = None,
    year: int | None = None,
    asset_type: str | None = None,
    dividend_type: DividendType | None = None,
) -> tuple[list[PortfolioDividendEntitlement], date]:
    today = date.today()
    items = await load_portfolio_dividend_entitlements(db, portfolio_id)
    return (
        [
            item
            for item in items
            if _matches(
                item,
                today=today,
                status=status,
                year=year,
                asset_type=asset_type,
                dividend_type=dividend_type,
            )
        ],
        today,
    )


def _eligible_cash(
    items: Iterable[PortfolioDividendEntitlement],
) -> list[PortfolioDividendEntitlement]:
    return [
        item for item in items if item.entitlement.reason is EntitlementReason.ELIGIBLE
    ]


async def get_summary(
    db: AsyncSession,
    portfolio_id: int,
    status: DividendStatus | None = None,
    year: int | None = None,
    asset_type: str | None = None,
    dividend_type: DividendType | None = None,
) -> dict:
    items, today = await _load_filtered(
        db,
        portfolio_id,
        status=status,
        year=year,
        asset_type=asset_type,
        dividend_type=dividend_type,
    )
    cash_items = _eligible_cash(items)
    received = [
        item
        for item in cash_items
        if _payment_status(item, today=today) is DividendStatus.RECEBIDO
    ]
    pending = [
        item
        for item in cash_items
        if _payment_status(item, today=today) is DividendStatus.A_RECEBER
    ]
    start_12m = today - relativedelta(months=12)
    received_12m = [
        item
        for item in received
        if item.event.payment_date is not None and item.event.payment_date >= start_12m
    ]

    total_recebido = sum((item.entitlement.net_amount for item in received), Decimal(0))
    bruto_recebido = sum(
        (item.entitlement.gross_amount for item in received), Decimal(0)
    )
    total_pendente = sum((item.entitlement.net_amount for item in pending), Decimal(0))
    bruto_pendente = sum(
        (item.entitlement.gross_amount for item in pending), Decimal(0)
    )
    total_12m = sum((item.entitlement.net_amount for item in received_12m), Decimal(0))
    return {
        "total_recebido": float(total_recebido),
        "total_liquido_recebido": float(total_recebido),
        "total_bruto_recebido": float(bruto_recebido),
        "total_a_receber": float(total_pendente),
        "total_liquido_a_receber": float(total_pendente),
        "total_bruto_a_receber": float(bruto_pendente),
        "total_12m": float(total_12m),
        "media_mensal_12m": round(float(total_12m) / 12, 2),
        "eventos_nao_cash": sum(
            item.entitlement.reason is EntitlementReason.NON_CASH_EVENT
            for item in items
        ),
    }


async def list_items(
    db: AsyncSession,
    portfolio_id: int,
    status: DividendStatus | None = None,
    year: int | None = None,
    asset_type: str | None = None,
    dividend_type: DividendType | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    items, today = await _load_filtered(
        db,
        portfolio_id,
        status=status,
        year=year,
        asset_type=asset_type,
        dividend_type=dividend_type,
    )
    visible = [
        item
        for item in items
        if item.entitlement.reason
        in {EntitlementReason.ELIGIBLE, EntitlementReason.NON_CASH_EVENT}
    ]
    visible.sort(
        key=lambda item: (
            item.event.payment_date or date.min,
            item.event.ex_date,
            item.event.event_id,
        ),
        reverse=True,
    )
    start = (page - 1) * page_size
    page_items = visible[start:start + page_size]
    return {
        "total": len(visible),
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": item.event.event_id,
                "ticker": item.ticker,
                "asset_type": item.asset_type,
                "dividend_type": _enum_text(item.event.event_type),
                "is_cash": (
                    item.entitlement.reason is not EntitlementReason.NON_CASH_EVENT
                ),
                "status": _payment_status(item, today=today),
                "record_date": item.event.record_date,
                "ex_date": item.event.ex_date,
                "payment_date": item.event.payment_date,
                "approved_on": item.approved_on,
                "quantity": float(item.entitlement.eligible_quantity),
                "value_per_unit": float(item.event.value_per_unit),
                "gross_value_per_unit": _optional_float(item.gross_value_per_unit),
                "factor": _optional_float(item.factor),
                "complete_factor": _optional_float(item.complete_factor),
                "total_value": float(item.entitlement.gross_amount),
                "net_value": float(item.entitlement.net_amount),
                "isin_code": item.isin_code,
                "asset_issued": item.asset_issued,
                "related_to": item.related_to,
                "remarks": item.remarks,
            }
            for item in page_items
        ],
    }


async def get_monthly_history(
    db: AsyncSession,
    portfolio_id: int,
    status: DividendStatus | None = None,
    year: int | None = None,
    asset_type: str | None = None,
    dividend_type: DividendType | None = None,
) -> list[dict]:
    items, _ = await _load_filtered(
        db,
        portfolio_id,
        status=status,
        year=year,
        asset_type=asset_type,
        dividend_type=dividend_type,
    )
    data: dict[int, dict[int, dict[str, Decimal]]] = {}
    for item in _eligible_cash(items):
        payment_date = item.event.payment_date
        value = item.entitlement.net_amount.quantize(
            _MONEY_STEP, rounding=ROUND_HALF_UP
        )
        if payment_date is None or value <= 0:
            continue
        class_values = data.setdefault(payment_date.year, {}).setdefault(
            payment_date.month, {}
        )
        class_values[item.asset_type] = (
            class_values.get(item.asset_type, Decimal(0)) + value
        )
    return _monthly_payload(data)


def _monthly_payload(
    data: dict[int, dict[int, dict[str, Decimal]]],
) -> list[dict]:
    result = []
    for year_value in sorted(data, reverse=True):
        months: list[float | None] = []
        details = []
        for month in range(1, 13):
            values = data[year_value].get(month)
            if not values:
                months.append(None)
                continue
            by_class = sorted(
                (
                    {
                        "asset_type": kind,
                        "label": asset_type_label(kind),
                        "value": float(value.quantize(_MONEY_STEP)),
                    }
                    for kind, value in values.items()
                    if value > 0
                ),
                key=lambda item: (-item["value"], item["label"]),
            )
            total = round(sum(item["value"] for item in by_class), 2)
            months.append(total)
            details.append({"month": month, "total": total, "by_asset_class": by_class})
        populated = [value for value in months if value is not None]
        total = round(sum(populated), 2)
        result.append(
            {
                "year": year_value,
                "months": months,
                "total": total,
                "media": round(total / len(populated), 2) if populated else 0,
                "month_details": details,
            }
        )
    return result


async def get_distribution(
    db: AsyncSession,
    portfolio_id: int,
    months: int = 12,
    status: DividendStatus | None = None,
    year: int | None = None,
    asset_type: str | None = None,
    dividend_type: DividendType | None = None,
) -> list[dict]:
    items, today = await _load_filtered(
        db,
        portfolio_id,
        status=status,
        year=year,
        asset_type=asset_type,
        dividend_type=dividend_type,
    )
    start = today - relativedelta(months=months)
    totals: dict[tuple[str, str], Decimal] = {}
    for item in _eligible_cash(items):
        payment_date = item.event.payment_date
        if payment_date is None or (year is None and payment_date < start):
            continue
        key = (item.ticker, item.asset_type)
        totals[key] = totals.get(key, Decimal(0)) + item.entitlement.net_amount
    grand_total = sum(totals.values(), Decimal(0))
    if grand_total <= 0:
        return []
    return [
        {
            "ticker": ticker,
            "asset_type": kind,
            "total": round(float(total), 2),
            "percentage": round(float(total / grand_total * 100), 2),
        }
        for (ticker, kind), total in sorted(
            totals.items(), key=lambda item: item[1], reverse=True
        )
    ]


def _optional_float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)
