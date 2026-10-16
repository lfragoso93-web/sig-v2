"""Read-only audit of official Treasury coupon-payment facts.

The Tesouro Transparente dataset is aggregate market evidence.  It identifies
the title, payment date and gross unit value, but it does not identify the
portfolio eligibility cutoff.  Consequently this module never builds an
``AssetDividend`` or writes to the database.
"""
from __future__ import annotations

import csv
import io
import unicodedata
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

PACKAGE_ENDPOINT = (
    "https://www.tesourotransparente.gov.br/ckan/api/3/action/package_show"
)
DATASET_ID = "resgates-do-tesouro-direto"
AUDIT_SCHEMA_VERSION = "treasury-cash-event-source-audit.v1"


def _normalized(value: object) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in raw if not unicodedata.combining(ch)).strip().lower()


def _parse_timestamp(value: object) -> datetime:
    raw = str(value or "").strip().replace("Z", "+00:00")
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def select_latest_coupon_resource(payload: object) -> dict[str, str] | None:
    """Select the newest official coupon CSV from a CKAN package payload."""
    if not isinstance(payload, dict) or payload.get("success") is not True:
        return None
    result = payload.get("result")
    resources = result.get("resources") if isinstance(result, dict) else None
    if not isinstance(resources, list):
        return None

    candidates: list[dict[str, Any]] = []
    for item in resources:
        if not isinstance(item, dict):
            continue
        name = _normalized(item.get("name"))
        fmt = _normalized(item.get("format"))
        url = str(item.get("url") or "").strip()
        if "cupom" not in name or "juros" not in name or fmt != "csv" or not url:
            continue
        candidates.append(item)
    if not candidates:
        return None

    selected = max(candidates, key=lambda item: _parse_timestamp(item.get("last_modified")))
    return {
        "resource_id": str(selected.get("id") or ""),
        "url": str(selected.get("url") or ""),
        "last_modified": str(selected.get("last_modified") or ""),
    }


def _parse_date(value: object) -> date:
    return (
        datetime.strptime(str(value or "").strip(), "%d/%m/%Y")
        .replace(tzinfo=timezone.utc)
        .date()
    )


def _parse_decimal(value: object) -> Decimal:
    raw = str(value or "").strip().replace(".", "").replace(",", ".")
    parsed = Decimal(raw)
    if not parsed.is_finite() or parsed <= 0:
        raise InvalidOperation
    return parsed


def inspect_coupon_payment_csv(text: str) -> dict[str, object]:
    """Describe usable facts and blockers without producing persistable events."""
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    headers = [str(value or "").strip() for value in (reader.fieldnames or [])]
    expected = {
        "tipo titulo",
        "vencimento do titulo",
        "data resgate",
        "pu",
        "quantidade",
        "valor",
    }
    normalized_headers = {_normalized(value) for value in headers}
    if not expected.issubset(normalized_headers):
        missing = sorted(expected - normalized_headers)
        return {
            "headers": headers,
            "rows_seen": 0,
            "facts_accepted": 0,
            "facts_rejected": 0,
            "latest_payment_date": None,
            "status": "invalid_source_schema",
            "blockers": [f"missing required columns: {', '.join(missing)}"],
            "promotable_events": 0,
            "database_writes_executed": 0,
        }

    rows_seen = 0
    accepted = 0
    rejected = 0
    latest: date | None = None
    for row in reader:
        rows_seen += 1
        normalized_row = {_normalized(key): value for key, value in row.items()}
        try:
            title = str(normalized_row["tipo titulo"] or "").strip()
            _parse_date(normalized_row["vencimento do titulo"])
            payment_date = _parse_date(normalized_row["data resgate"])
            unit_value = _parse_decimal(normalized_row["pu"])
            quantity = _parse_decimal(normalized_row["quantidade"])
            aggregate_value = _parse_decimal(normalized_row["valor"])
            if not title:
                raise ValueError
            tolerance = Decimal("0.02")
            if abs((unit_value * quantity) - aggregate_value) > tolerance:
                raise ValueError
        except (KeyError, InvalidOperation, ValueError):
            rejected += 1
            continue
        accepted += 1
        latest = payment_date if latest is None or payment_date > latest else latest

    return {
        "headers": headers,
        "rows_seen": rows_seen,
        "facts_accepted": accepted,
        "facts_rejected": rejected,
        "latest_payment_date": latest.isoformat() if latest else None,
        "capabilities": {
            "title_identity": True,
            "maturity_date": True,
            "payment_date": True,
            "gross_value_per_unit": True,
            "record_date": False,
            "portfolio_eligibility": False,
            "taxable_income_per_unit": False,
        },
        "status": "blocked_missing_eligibility",
        "blockers": [
            "official source does not publish record_date",
            "aggregate quantity does not identify portfolio eligibility",
            "official source does not split taxable income per unit",
        ],
        "promotable_events": 0,
        "database_writes_executed": 0,
    }


async def audit_official_coupon_payments() -> dict[str, object]:
    """Fetch and inspect the official source without any database dependency."""
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        package = await client.get(PACKAGE_ENDPOINT, params={"id": DATASET_ID})
        package.raise_for_status()
        resource = select_latest_coupon_resource(package.json())
        if resource is None:
            return {
                "schema_version": AUDIT_SCHEMA_VERSION,
                "source": "tesouro_transparente",
                "status": "source_unavailable",
                "promotable_events": 0,
                "database_writes_executed": 0,
            }
        response = await client.get(resource["url"], timeout=90.0)
        response.raise_for_status()
        report = inspect_coupon_payment_csv(response.text)
        return {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "source": "tesouro_transparente",
            "dataset_id": DATASET_ID,
            "resource": resource,
            **report,
        }
