"""Modelo e normalização canônicos de eventos globais de Proventos."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from app.models.dividend_enums import DividendType
from app.services.dividend_type_service import normalize_dividend_type


@dataclass
class ParsedDividendEvent:
    record_date: date | None
    ex_date: date
    payment_date: date | None
    approved_on: date | None
    value_per_unit: float
    dividend_type: str
    gross_value_per_unit: float | None = None
    factor: float | None = None
    complete_factor: float | None = None
    isin_code: str | None = None
    asset_issued: str | None = None
    related_to: str | None = None
    remarks: str | None = None
    raw_payload: dict[str, Any] | None = None

    def __iter__(self):
        yield self.record_date
        yield self.ex_date
        yield self.payment_date
        yield self.value_per_unit
        yield self.dividend_type


def _map_dividend_type(raw: str | None, category: str | None = None) -> str:
    return normalize_dividend_type(raw, category).value


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _next_business_day(value: date) -> date:
    next_date = value + timedelta(days=1)
    while next_date.weekday() >= 5:
        next_date += timedelta(days=1)
    return next_date


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_dividend_event(raw: dict[str, Any]) -> ParsedDividendEvent | None:
    """Normaliza um payload de provider sem persistência ou acesso externo."""
    try:
        category = raw.get("eventCategory")
        record_date = _parse_date(
            raw.get("lastDatePrior")
            or raw.get("recordDate")
            or raw.get("dateCom")
            or raw.get("date_with")
        )
        explicit_ex_date = _parse_date(
            raw.get("exDate")
            or raw.get("ex_date")
            or raw.get("dateEx")
            or raw.get("date_ex")
        )
        payment_date = _parse_date(
            raw.get("paymentDate")
            or raw.get("paidAt")
            or raw.get("payment_date")
        )
        approved_on = _parse_date(
            raw.get("approvedOn")
            or raw.get("approved_on")
            or raw.get("declaredDate")
        )

        if explicit_ex_date:
            ex_date = explicit_ex_date
        elif record_date:
            ex_date = _next_business_day(record_date)
        elif payment_date:
            ex_date = payment_date
        elif approved_on:
            ex_date = approved_on
        else:
            return None

        dividend_type = _map_dividend_type(
            raw.get("label") or raw.get("type") or raw.get("dividendType"),
            category,
        )
        value = _to_float(
            raw.get("rate")
            or raw.get("value")
            or raw.get("amount")
            or raw.get("income"),
            default=0.0,
        )
        factor = _to_optional_float(raw.get("factor"))
        complete_factor = _to_optional_float(
            raw.get("completeFactor") or raw.get("complete_factor")
        )

        cash_types = {
            DividendType.DIVIDENDO.value,
            DividendType.JCP.value,
            DividendType.RENDIMENTO.value,
            DividendType.AMORTIZACAO.value,
            DividendType.OUTROS.value,
        }
        if dividend_type in cash_types and value <= 0:
            return None

        return ParsedDividendEvent(
            record_date=record_date,
            ex_date=ex_date,
            payment_date=payment_date,
            approved_on=approved_on,
            value_per_unit=value,
            gross_value_per_unit=_to_optional_float(
                raw.get("grossRate") or raw.get("grossValue")
            ),
            factor=factor,
            complete_factor=complete_factor,
            dividend_type=dividend_type,
            isin_code=raw.get("isinCode") or raw.get("isin_code"),
            asset_issued=raw.get("assetIssued") or raw.get("asset_issued"),
            related_to=raw.get("relatedTo") or raw.get("related_to"),
            remarks=raw.get("remarks") or raw.get("observation"),
            raw_payload=raw,
        )
    except Exception:
        return None
