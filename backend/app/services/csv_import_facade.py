"""Fachada de importação CSV com resolução temporal de tickers."""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.services.csv_import_service import (
    CSVImportError,
    _read_upload_text,
    _safe_float,
    _validate_duplicate_transactions,
    _validate_writer_preflight,
    import_csv_transactions,
    parse_csv_content,
)
from app.services.csv_import_service import (
    export_transactions_csv as _export_transactions_csv,
    generate_csv_template as _generate_csv_template,
)
from app.services.csv_ticker_resolution import enrich_csv_dry_run_with_ticker_resolution
from app.services.ticker_change_event_service import register_ticker_change
from app.services.ticker_change_processor import apply_pending_ticker_changes
from app.services.ticker_resolution_service import ResolvedTicker
from app.services.b3_investor_area_adapter_service import (
    adapt_b3_investor_csv_to_canonical,
    is_b3_csv_content,
)


def generate_csv_template() -> str:
    return _generate_csv_template()


async def export_transactions_csv(db: AsyncSession, portfolio_id: int) -> str:
    return await _export_transactions_csv(db, portfolio_id)


async def _build_dry_run_result(
    content: str,
    *,
    portfolio_id: int,
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    portfolio_result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if portfolio_result.scalar_one_or_none() is None:
        return {
            "success": False,
            "imported_count": 0,
            "skipped_count": 0,
            "error_count": 1,
            "rows": [],
            "global_errors": ["Carteira não encontrada"],
        }

    rows, global_errors = await parse_csv_content(content, portfolio_id, db)
    if not global_errors and not any(row.errors or row.warnings for row in rows):
        await _validate_duplicate_transactions(rows, portfolio_id, db)
    if not global_errors:
        await _validate_writer_preflight(rows, db)
    response_rows: list[dict[str, Any]] = []
    error_count = len(global_errors)
    skipped_count = 0

    for row in rows:
        if row.errors:
            status = "error"
            error_count += 1
        elif row.warnings:
            status = "warning"
            skipped_count += 1
        else:
            status = "valid"

        response_rows.append({
            "row_num": row.row_num,
            "errors": row.errors,
            "warnings": row.warnings,
            "status": status,
            "ticker": (row.data.get("ticker") or "").strip().upper() or None,
            "asset_type": (row.data.get("asset_type") or "").strip().upper() or None,
            "date": (row.data.get("date") or "").strip() or None,
            "operation": (row.data.get("operation") or "").strip().lower() or None,
            "quantity": _safe_float(row.data.get("quantity")),
        })

    result = {
        "success": error_count == 0 and skipped_count == 0,
        "imported_count": 0,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "rows": response_rows,
        "global_errors": global_errors,
    }
    return await enrich_csv_dry_run_with_ticker_resolution(result)


async def _register_historical_aliases(
    result: dict[str, Any],
    *,
    portfolio_id: int,
    db: AsyncSession,
) -> None:
    for row in result.get("rows", []):
        if row.get("ticker_resolution_status") != "historical_alias":
            continue

        ticker = str(row.get("ticker") or "").upper()
        asset_type = str(row.get("asset_type") or "").upper()
        current_ticker = str(row.get("resolved_ticker") or "").upper()
        effective_date_raw = row.get("ticker_effective_date")
        if not ticker or not asset_type or not current_ticker or not effective_date_raw:
            continue

        effective_date = date.fromisoformat(str(effective_date_raw))
        old_asset_result = await db.execute(
            select(Asset).where(
                Asset.ticker == ticker,
                Asset.asset_type == asset_type,
            )
        )
        old_asset = old_asset_result.scalar_one_or_none()
        if old_asset is None:
            old_asset = Asset(ticker=ticker, asset_type=asset_type, currency="BRL")
            db.add(old_asset)
            await db.flush()

        await register_ticker_change(
            db,
            portfolio_id=portfolio_id,
            old_asset=old_asset,
            resolution=ResolvedTicker(
                requested_ticker=ticker,
                current_ticker=current_ticker,
                changed=True,
                status="renamed",
                effective_date=effective_date,
            ),
        )


async def import_transactions_csv(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
    file: Any,
    dry_run: bool = True,
    source: str = "auto",
) -> dict[str, Any]:
    try:
        content = await _read_upload_text(file)
    except CSVImportError as exc:
        return {
            "success": False,
            "imported_count": 0,
            "skipped_count": 0,
            "error_count": 1,
            "rows": [],
            "global_errors": [str(exc)],
        }

    adapter_format = None
    skipped_records = None
    if source == "b3" or (source == "auto" and is_b3_csv_content(content)):
        b3_result = adapt_b3_investor_csv_to_canonical(content)
        if not b3_result.success and b3_result.errors:
            return {
                "success": False,
                "imported_count": 0,
                "skipped_count": 0,
                "error_count": len(b3_result.errors),
                "rows": [],
                "global_errors": b3_result.errors,
                "adapter_format": b3_result.format_detected,
                "skipped_records": [item.to_dict() for item in b3_result.skipped_items],
            }
        content = b3_result.canonical_csv
        adapter_format = b3_result.format_detected
        skipped_records = [item.to_dict() for item in b3_result.skipped_items]

    validation = await _build_dry_run_result(
        content,
        portfolio_id=portfolio_id,
        user_id=user_id,
        db=db,
    )
    if adapter_format:
        validation["adapter_format"] = adapter_format
    if skipped_records is not None:
        validation["skipped_records"] = skipped_records

    if dry_run or not validation.get("success"):
        return validation

    await _register_historical_aliases(
        validation,
        portfolio_id=portfolio_id,
        db=db,
    )
    result = await import_csv_transactions(
        content=content,
        portfolio_id=portfolio_id,
        user_id=user_id,
        db=db,
    )
    if adapter_format:
        result["adapter_format"] = adapter_format
    if skipped_records is not None:
        result["skipped_records"] = skipped_records

    if result.get("success"):
        await apply_pending_ticker_changes(db, portfolio_id)
        await db.commit()
    return result
