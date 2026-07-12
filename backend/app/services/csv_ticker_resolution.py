"""Enriquece o dry-run do CSV com resolucao de tickers, sem persistir dados."""

from datetime import date, datetime
from typing import Any, Optional

from app.services.ticker_resolution_service import TickerResolutionService


def _operation_date(row: dict[str, Any]) -> Optional[date]:
    raw = row.get("date") or row.get("operation_date") or row.get("transaction_date")
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if not raw:
        return None
    value = str(raw).strip()
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%d/%m/%Y").date()
        except ValueError:
            return None


async def enrich_csv_dry_run_with_ticker_resolution(
    result: dict[str, Any],
    *,
    service: Optional[TickerResolutionService] = None,
) -> dict[str, Any]:
    rows = result.get("rows")
    if not isinstance(rows, list) or result.get("global_errors"):
        return result

    tickers = [
        str(row.get("ticker") or "")
        for row in rows
        if isinstance(row, dict) and not row.get("errors") and row.get("ticker")
    ]
    if not tickers:
        return result

    resolutions = await (service or TickerResolutionService()).resolve_many(tickers)
    added_warnings = 0

    for row in rows:
        if not isinstance(row, dict) or row.get("errors"):
            continue

        ticker = str(row.get("ticker") or "").strip().upper()
        resolution = resolutions.get(ticker)
        if resolution is None or not resolution.changed:
            continue

        row["resolved_ticker"] = resolution.current_ticker
        row["ticker_resolution_status"] = resolution.status

        operation_date = _operation_date(row)
        if (
            resolution.effective_date is not None
            and operation_date is not None
            and operation_date < resolution.effective_date
        ):
            row["ticker_resolution_status"] = "historical_alias"
            continue

        warnings = row.setdefault("warnings", [])
        message = (
            f"O ticker '{resolution.requested_ticker}' foi renomeado para "
            f"'{resolution.current_ticker}'. Atualize o CSV antes de importar."
        )
        if message not in warnings:
            warnings.append(message)
            added_warnings += 1

        row["status"] = "warning"

    if added_warnings:
        result["skipped_count"] = int(result.get("skipped_count", 0)) + added_warnings
        result["success"] = False

    return result
