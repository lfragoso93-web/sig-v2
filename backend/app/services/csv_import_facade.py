"""Fachada de importação CSV com resolução temporal de tickers."""

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.services import csv_import_service as legacy_csv_import_service
from app.services.csv_ticker_resolution import enrich_csv_dry_run_with_ticker_resolution
from app.services.ticker_change_event_service import register_ticker_change
from app.services.ticker_resolution_service import ResolvedTicker


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

    rows, global_errors = await legacy_csv_import_service.parse_csv_content(
        content,
        portfolio_id,
        db,
    )
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
            "quantity": legacy_csv_import_service._safe_float(row.data.get("quantity")),
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
) -> dict[str, Any]:
    try:
        content = await legacy_csv_import_service._read_upload_text(file)
    except legacy_csv_import_service.CSVImportError as exc:
        return {
            "success": False,
            "imported_count": 0,
            "skipped_count": 0,
            "error_count": 1,
            "rows": [],
            "global_errors": [str(exc)],
        }

    validation = await _build_dry_run_result(
        content,
        portfolio_id=portfolio_id,
        user_id=user_id,
        db=db,
    )
    if dry_run or not validation.get("success"):
        return validation

    await _register_historical_aliases(validation, db=db)
    return await legacy_csv_import_service.import_csv_transactions(
        content=content,
        portfolio_id=portfolio_id,
        user_id=user_id,
        db=db,
    )
