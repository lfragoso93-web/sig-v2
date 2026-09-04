import csv
import io
from datetime import datetime, date as DateType
from typing import Tuple, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction, OperationType
from app.models.asset import Asset, AssetType
from app.models.portfolio import Portfolio
from sqlalchemy import select
from app.core.log_safety import sanitize_log_value
from app.services.portfolio_service import invalidate_portfolio_cache
import logging

logger = logging.getLogger(__name__)

SUPPORTED_ASSET_TYPES = [at.value for at in AssetType]
VALID_OPERATIONS = [op.value for op in OperationType]
CSV_TEMPLATE_HEADERS = [
    "ticker",
    "asset_type",
    "operation",
    "quantity",
    "price",
    "date",
    "fees",
    "currency",
    "notes",
]


def generate_csv_template() -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(CSV_TEMPLATE_HEADERS)

    writer.writerow([
        "PETR4",
        "ACAO",
        "buy",
        "100",
        "25.50",
        "2024-01-15",
        "10.00",
        "BRL",
        "Compra inicial",
    ])
    writer.writerow([
        "VALE3",
        "ACAO",
        "buy",
        "50",
        "80.00",
        "2024-02-20",
        "5.00",
        "BRL",
        "",
    ])
    writer.writerow([
        "IVVB11",
        "ETF_NACIONAL",
        "buy",
        "10",
        "100.50",
        "2024-03-10",
        "0.00",
        "BRL",
        "ETF S&P500",
    ])

    return output.getvalue()


class CSVImportError(Exception):
    pass


class CSVRow:
    def __init__(self, row_num: int, data: Dict[str, Any]):
        self.row_num = row_num
        self.data = data
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, message: str):
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def is_valid(self) -> bool:
        return len(self.errors) == 0


async def _read_upload_text(file: Any) -> str:
    """Le um UploadFile e devolve texto CSV, aceitando BOM UTF-8 e Latin-1."""
    raw = await file.read()
    if not raw:
        raise CSVImportError("O arquivo CSV está vazio")

    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise CSVImportError("Não foi possível identificar a codificação do arquivo CSV")


async def import_transactions_csv(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
    file: Any,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Entrada usada pelo endpoint multipart de importação.

    No dry-run apenas valida o conteúdo. Na importação efetiva delega para a
    rotina transacional existente, preservando uma única regra de persistência.
    """
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

    if not dry_run:
        return await import_csv_transactions(
            content=content,
            portfolio_id=portfolio_id,
            user_id=user_id,
            db=db,
        )

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
    response_rows = []
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
            "operation": (row.data.get("operation") or "").strip().lower() or None,
            "quantity": _safe_float(row.data.get("quantity")),
        })

    return {
        "success": error_count == 0 and skipped_count == 0,
        "imported_count": 0,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "rows": response_rows,
        "global_errors": global_errors,
    }


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def parse_csv_content(
    content: str,
    portfolio_id: int,
    db: AsyncSession,
) -> Tuple[List[CSVRow], List[str]]:
    """
    Parse CSV content and validate each row.
    Returns (rows_with_validation, global_errors)
    """
    rows = []
    global_errors = []

    try:
        csv_reader = csv.DictReader(io.StringIO(content))

        if csv_reader.fieldnames is None:
            global_errors.append("CSV file is empty or invalid")
            return rows, global_errors

        missing_headers = set(CSV_TEMPLATE_HEADERS) - set(csv_reader.fieldnames)
        if missing_headers:
            global_errors.append(f"Missing required headers: {', '.join(missing_headers)}")
            return rows, global_errors

        for row_num, raw_row in enumerate(csv_reader, start=2):
            csv_row = CSVRow(row_num, raw_row)

            if not any(raw_row.values()):
                csv_row.add_warning("Empty row, skipping")
                rows.append(csv_row)
                continue

            ticker = raw_row.get("ticker", "").strip().upper()
            asset_type = raw_row.get("asset_type", "").strip().upper()
            operation = raw_row.get("operation", "").strip().lower()
            quantity_str = raw_row.get("quantity", "").strip()
            price_str = raw_row.get("price", "").strip()
            date_str = raw_row.get("date", "").strip()
            fees_str = raw_row.get("fees", "0").strip()
            currency = raw_row.get("currency", "BRL").strip().upper()
            if not ticker:
                csv_row.add_error("ticker is required")

            if not asset_type:
                csv_row.add_error("asset_type is required")
            elif asset_type not in SUPPORTED_ASSET_TYPES:
                csv_row.add_error(f"asset_type '{asset_type}' not supported. Valid: {', '.join(SUPPORTED_ASSET_TYPES)}")

            if not operation:
                csv_row.add_error("operation is required")
            elif operation not in VALID_OPERATIONS:
                csv_row.add_error(f"operation '{operation}' not valid. Valid: {', '.join(VALID_OPERATIONS)}")

            if not quantity_str:
                csv_row.add_error("quantity is required")
            else:
                try:
                    quantity = float(quantity_str)
                    if quantity <= 0:
                        csv_row.add_error("quantity must be positive")
                except ValueError:
                    csv_row.add_error(f"quantity '{quantity_str}' is not a valid number")

            if not price_str:
                csv_row.add_error("price is required")
            else:
                try:
                    price = float(price_str)
                    if price <= 0:
                        csv_row.add_error("price must be positive")
                except ValueError:
                    csv_row.add_error(f"price '{price_str}' is not a valid number")

            if not date_str:
                csv_row.add_error("date is required")
            else:
                try:
                    parsed_date = _parse_date(date_str)
                    if parsed_date > DateType.today():
                        csv_row.add_warning(f"date '{date_str}' is in the future")
                except ValueError:
                    csv_row.add_error(f"date '{date_str}' format not recognized (use YYYY-MM-DD)")

            if fees_str:
                try:
                    fees = float(fees_str)
                    if fees < 0:
                        csv_row.add_error("fees cannot be negative")
                except ValueError:
                    csv_row.add_error(f"fees '{fees_str}' is not a valid number")

            if currency not in ["BRL", "USD", "EUR", "BTC"]:
                csv_row.add_warning(f"currency '{currency}' may not be valid, defaulting to BRL")

            rows.append(csv_row)

    except Exception as e:
        global_errors.append(f"Error parsing CSV: {str(e)}")
        logger.error("CSV parse error: %s", sanitize_log_value(e))

    return rows, global_errors


def _parse_date(date_str: str) -> DateType:
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Cannot parse date: {date_str}")


async def import_csv_transactions(
    content: str,
    portfolio_id: int,
    user_id: int,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Import transactions from CSV content.
    Returns dict with import results and validation details.
    """
    result = {
        "success": False,
        "imported_count": 0,
        "skipped_count": 0,
        "error_count": 0,
        "rows": [],
        "global_errors": [],
    }

    portfolio = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id)
    )
    portfolio_obj = portfolio.scalar_one_or_none()
    if not portfolio_obj:
        result["global_errors"].append(f"Portfolio {portfolio_id} not found")
        return result

    if portfolio_obj.user_id != user_id:
        result["global_errors"].append("Unauthorized: Portfolio belongs to different user")
        return result

    rows, global_errors = await parse_csv_content(content, portfolio_id, db)
    result["global_errors"] = global_errors

    blocking_rows = [row for row in rows if row.errors or row.warnings]
    if global_errors or blocking_rows:
        result["error_count"] += len(global_errors) + sum(1 for row in rows if row.errors)
        result["skipped_count"] += sum(1 for row in rows if row.warnings and not row.errors)
        result["rows"] = [
            {
                "row_num": r.row_num,
                "errors": r.errors,
                "warnings": r.warnings,
                "status": "error" if r.errors else "warning" if r.warnings else "valid",
            }
            for r in rows
        ]
        return result

    created_transactions = []

    for csv_row in rows:
        if csv_row.warnings and not csv_row.errors:
            result["rows"].append({
                "row_num": csv_row.row_num,
                "errors": csv_row.errors,
                "warnings": csv_row.warnings,
                "status": "warning",
            })
            result["skipped_count"] += 1
            continue

        if not csv_row.is_valid():
            result["rows"].append({
                "row_num": csv_row.row_num,
                "errors": csv_row.errors,
                "warnings": csv_row.warnings,
                "status": "error",
            })
            result["error_count"] += 1
            continue

        try:
            ticker = csv_row.data.get("ticker", "").strip().upper()
            asset_type = csv_row.data.get("asset_type", "").strip().upper()
            operation = csv_row.data.get("operation", "").strip().lower()
            quantity = float(csv_row.data.get("quantity", 0))
            price = float(csv_row.data.get("price", 0))
            date_str = csv_row.data.get("date", "").strip()
            fees = float(csv_row.data.get("fees", 0) or 0)
            currency = csv_row.data.get("currency", "BRL").strip().upper()
            notes = csv_row.data.get("notes", "").strip()

            parsed_date = _parse_date(date_str)

            existing_transaction = await db.execute(
                select(Transaction).where(
                    Transaction.portfolio_id == portfolio_id,
                    Transaction.ticker == ticker,
                    Transaction.asset_type == asset_type,
                    Transaction.operation == operation,
                    Transaction.quantity == quantity,
                    Transaction.price == price,
                    Transaction.date == parsed_date,
                    Transaction.fees == fees,
                    Transaction.currency == currency,
                )
            )
            if existing_transaction.scalar_one_or_none() is not None:
                result["rows"].append({
                    "row_num": csv_row.row_num,
                    "errors": [],
                    "warnings": ["duplicate transaction skipped"],
                    "status": "skipped",
                    "ticker": ticker,
                    "operation": operation,
                    "quantity": quantity,
                })
                result["skipped_count"] += 1
                continue

            asset = await db.execute(
                select(Asset).where(
                    (Asset.ticker == ticker) & (Asset.asset_type == asset_type)
                )
            )
            asset_obj = asset.scalar_one_or_none()

            if not asset_obj:
                asset_obj = Asset(
                    ticker=ticker,
                    asset_type=asset_type,
                    currency=currency,
                )
                db.add(asset_obj)
                await db.flush()

            transaction = Transaction(
                portfolio_id=portfolio_id,
                ticker=ticker,
                asset_type=asset_type,
                operation=operation,
                quantity=quantity,
                price=price,
                fees=fees,
                date=parsed_date,
                currency=currency,
                notes=notes if notes else None,
            )
            db.add(transaction)
            created_transactions.append(transaction)

            result["rows"].append({
                "row_num": csv_row.row_num,
                "errors": [],
                "warnings": [],
                "status": "imported",
                "ticker": ticker,
                "operation": operation,
                "quantity": quantity,
            })
            result["imported_count"] += 1

        except Exception as e:
            logger.error(
                "Error importing row %d: %s",
                csv_row.row_num,
                sanitize_log_value(e),
            )
            result["rows"].append({
                "row_num": csv_row.row_num,
                "errors": [str(e)],
                "warnings": [],
                "status": "error",
            })
            result["error_count"] += 1

    if created_transactions:
        try:
            await db.commit()
            result["success"] = True
            await invalidate_portfolio_cache(portfolio_id)
            logger.info(
                "Imported %d transactions for portfolio %s",
                len(created_transactions),
                sanitize_log_value(portfolio_id),
            )
        except Exception as e:
            await db.rollback()
            logger.error(
                "Error committing transactions: %s",
                sanitize_log_value(e),
            )
            result["success"] = False
            result["error_count"] += len(created_transactions)
            result["imported_count"] = 0
            result["global_errors"].append(f"Database error: {str(e)}")
    else:
        result["success"] = result["error_count"] == 0

    return result
