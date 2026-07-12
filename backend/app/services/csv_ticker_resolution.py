"""Enriquece o dry-run do CSV com resolucao de tickers, sem persistir dados."""

from typing import Any, Optional

from app.services.ticker_resolution_service import TickerResolutionService


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

        warnings = row.setdefault("warnings", [])
        message = (
            f"O ticker '{resolution.requested_ticker}' foi renomeado para "
            f"'{resolution.current_ticker}'. Atualize o CSV antes de importar."
        )
        if message not in warnings:
            warnings.append(message)
            added_warnings += 1

        row["resolved_ticker"] = resolution.current_ticker
        row["ticker_resolution_status"] = resolution.status
        row["status"] = "warning"

    if added_warnings:
        result["skipped_count"] = int(result.get("skipped_count", 0)) + added_warnings
        result["success"] = False

    return result
