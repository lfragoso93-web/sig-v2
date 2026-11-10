"""Fachada de importação CSV, XLSX e PDF com suporte a B3 e Notas de Corretagem."""

import csv
import io
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.portfolio import Portfolio
from app.services.csv_import_service import (
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
    adapt_b3_investor_xlsx_to_canonical,
    adapt_b3_investor_pdf_to_canonical,
    is_b3_csv_content,
)
from app.services.brokerage_note_adapter_service import (
    adapt_brokerage_note_to_canonical,
    is_brokerage_note_content,
    extract_text_from_pdf,
)

try:
    import openpyxl
except ImportError:
    openpyxl = None  # type: ignore[assignment]


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
    if not global_errors and not any(row.errors or row.warnings for row in rows):
        original_types = [row.data.get("asset_type") for row in rows]
        await _validate_writer_preflight(rows, db, portfolio_id=portfolio_id)
        reconciled_types = [row.data.get("asset_type") for row in rows]
        if (
            not any(row.errors or row.warnings for row in rows)
            and reconciled_types != original_types
        ):
            await _validate_duplicate_transactions(rows, portfolio_id, db)
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
    if hasattr(file, "read"):
        raw_bytes = await file.read()
    elif isinstance(file, bytes):
        raw_bytes = file
    elif isinstance(file, str):
        raw_bytes = file.encode("utf-8")
    else:
        raw_bytes = b""

    if not raw_bytes:
        return {
            "success": False,
            "imported_count": 0,
            "skipped_count": 0,
            "error_count": 1,
            "rows": [],
            "global_errors": ["O arquivo CSV está vazio"],
        }

    raw_filename = getattr(file, "filename", None)
    filename = raw_filename.lower() if isinstance(raw_filename, str) else ""
    adapter_format = None
    skipped_records = None
    content = ""

    # A) Arquivo PDF (B3 Extrato ou Nota de Corretagem)
    if raw_bytes.startswith(b"%PDF") or (bool(filename) and filename.endswith(".pdf")):
        extracted_text = ""
        try:
            extracted_text = extract_text_from_pdf(raw_bytes)
        except Exception as exc:
            return {
                "success": False,
                "imported_count": 0,
                "skipped_count": 0,
                "error_count": 1,
                "rows": [],
                "global_errors": [f"Falha ao ler arquivo PDF: {exc}"],
            }

        if is_brokerage_note_content(extracted_text):
            note_res = adapt_brokerage_note_to_canonical(extracted_text)
            if not note_res.success and note_res.errors:
                return {
                    "success": False,
                    "imported_count": 0,
                    "skipped_count": 0,
                    "error_count": len(note_res.errors),
                    "rows": [],
                    "global_errors": note_res.errors,
                    "adapter_format": note_res.format_detected,
                }
            content = note_res.canonical_csv
            adapter_format = note_res.format_detected
            skipped_records = [item.to_dict() for item in note_res.skipped_items]
        else:
            b3_pdf_res = adapt_b3_investor_pdf_to_canonical(raw_bytes)
            if not b3_pdf_res.success and b3_pdf_res.errors:
                return {
                    "success": False,
                    "imported_count": 0,
                    "skipped_count": 0,
                    "error_count": len(b3_pdf_res.errors),
                    "rows": [],
                    "global_errors": b3_pdf_res.errors,
                    "adapter_format": b3_pdf_res.format_detected,
                }
            content = b3_pdf_res.canonical_csv
            adapter_format = b3_pdf_res.format_detected
            skipped_records = [item.to_dict() for item in b3_pdf_res.skipped_items]

    # B) Arquivo Excel (.xlsx / .xls)
    elif raw_bytes.startswith(b"PK\x03\x04") or (bool(filename) and filename.endswith((".xlsx", ".xls"))):
        xlsx_res = adapt_b3_investor_xlsx_to_canonical(raw_bytes)
        if xlsx_res.success and xlsx_res.canonical_csv:
            content = xlsx_res.canonical_csv
            adapter_format = xlsx_res.format_detected
            skipped_records = [item.to_dict() for item in xlsx_res.skipped_items]
        else:
            try:
                if not openpyxl:
                    raise RuntimeError("openpyxl não instalado")
                wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)
                ws = wb.active
                raw_rows = []
                if ws:
                    for r in ws.iter_rows(values_only=True):
                        raw_rows.append([str(c) if c is not None else "" for c in r])
                if raw_rows and any("ticker" in str(c).lower() for c in raw_rows[0]):
                    out = io.StringIO()
                    writer = csv.writer(out)
                    for r in raw_rows:
                        writer.writerow(r)
                    content = out.getvalue()
                else:
                    return {
                        "success": False,
                        "imported_count": 0,
                        "skipped_count": 0,
                        "error_count": len(xlsx_res.errors) or 1,
                        "rows": [],
                        "global_errors": xlsx_res.errors or ["Formato de planilha não reconhecido."],
                        "adapter_format": "unknown_xlsx",
                    }
            except Exception as exc:
                return {
                    "success": False,
                    "imported_count": 0,
                    "skipped_count": 0,
                    "error_count": 1,
                    "rows": [],
                    "global_errors": [f"Erro ao processar planilha: {exc}"],
                }

    # C) Arquivo de Texto / CSV
    else:
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                content = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            return {
                "success": False,
                "imported_count": 0,
                "skipped_count": 0,
                "error_count": 1,
                "rows": [],
                "global_errors": ["Não foi possível identificar a codificação do arquivo."],
            }

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
        elif is_brokerage_note_content(content):
            note_res = adapt_brokerage_note_to_canonical(content)
            if not note_res.success and note_res.errors:
                return {
                    "success": False,
                    "imported_count": 0,
                    "skipped_count": 0,
                    "error_count": len(note_res.errors),
                    "rows": [],
                    "global_errors": note_res.errors,
                    "adapter_format": note_res.format_detected,
                }
            content = note_res.canonical_csv
            adapter_format = note_res.format_detected
            skipped_records = [item.to_dict() for item in note_res.skipped_items]

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
