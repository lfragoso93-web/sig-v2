import csv
import io
import logging
from datetime import date as DateType
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_safety import sanitize_log_value
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.fixed_income_contract import FixedIncomeContract
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.schemas.fixed_income_contract import FixedIncomeContractCreate
from app.schemas.transaction import TransactionCreate
from app.services.crypto_transaction_eligibility_service import (
    CryptoTransactionEligibilityError,
    require_catalog_crypto_asset,
)
from app.services.portfolio_service import invalidate_portfolio_cache
from app.services.transaction_write_service import (
    TransactionWriteError,
    add_transaction_record,
)
from app.services.treasury_catalog_service import resolve_treasury_symbol
from app.services.b3_investor_area_adapter_service import (
    adapt_b3_investor_csv_to_canonical,
    is_b3_csv_content,
)

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
    "fixed_income_contract_key",
    "fixed_income_product_type",
    "fixed_income_display_name",
    "fixed_income_issuer",
    "fixed_income_indexer",
    "fixed_income_rate_value",
    "fixed_income_rate_unit",
    "fixed_income_maturity_date",
    "fixed_income_liquidity_type",
    "fixed_income_grace_period_end",
    "fixed_income_tax_exempt",
    "fixed_income_currency",
]
CSV_REQUIRED_HEADERS = CSV_TEMPLATE_HEADERS[:9]
CSV_FIXED_INCOME_FIELDS = CSV_TEMPLATE_HEADERS[9:]
CRYPTO_TICKER_ALIASES = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "CARDANO": "ADA",
}
PRICE_HISTORY_REQUIRED_TYPES = {
    AssetType.ACAO.value,
    AssetType.BDR.value,
    AssetType.ETF_INTERNACIONAL.value,
    AssetType.ETF_NACIONAL.value,
    AssetType.FII.value,
    AssetType.STOCK.value,
}


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
        *([""] * len(CSV_FIXED_INCOME_FIELDS)),
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
        *([""] * len(CSV_FIXED_INCOME_FIELDS)),
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
        *([""] * len(CSV_FIXED_INCOME_FIELDS)),
    ])

    return output.getvalue()


class CSVImportError(Exception):
    pass


class CSVRow:
    def __init__(self, row_num: int, data: dict[str, Any]):
        self.row_num = row_num
        self.data = data
        self.errors: list[str] = []
        self.warnings: list[str] = []

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
    source: str = "auto",
) -> dict[str, Any]:
    """Entrada usada pelo endpoint multipart de importação.

    No dry-run valida o conteúdo e todos os blockers de persistência conhecidos.
    Na importação efetiva delega para a rotina transacional existente, preservando
    uma única regra de persistência.
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

    if not dry_run:
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
        return result

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
        await _validate_writer_preflight(rows, db)
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
        "adapter_format": adapter_format,
        "skipped_records": skipped_records,
    }


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_csv_ticker(ticker: str, asset_type: str) -> str:
    normalized = ticker.strip().upper()
    if asset_type.strip().upper() == AssetType.CRIPTO.value:
        return CRYPTO_TICKER_ALIASES.get(normalized, normalized)
    return normalized


async def _resolve_csv_ticker(ticker: str, asset_type: str, db: AsyncSession) -> str | None:
    normalized = _normalize_csv_ticker(ticker, asset_type)
    if asset_type.strip().upper() != AssetType.TESOURO_DIRETO.value or not normalized:
        return normalized
    return await resolve_treasury_symbol(db, ticker)


def _transaction_identity(row: CSVRow) -> tuple[str, str, str, float, float, DateType, float, str]:
    data = row.data
    return (
        data.get("ticker", "").strip().upper(),
        data.get("asset_type", "").strip().upper(),
        data.get("operation", "").strip().lower(),
        float(data.get("quantity", 0)),
        float(data.get("price", 0)),
        _parse_date(data.get("date", "").strip()),
        float(data.get("fees", 0) or 0),
        data.get("currency", "BRL").strip().upper(),
    )


async def _validate_duplicate_transactions(
    rows: list[CSVRow],
    portfolio_id: int,
    db: AsyncSession,
) -> None:
    """Marca duplicatas antes de qualquer persistência para manter o lote atômico."""
    seen: set[tuple[str, str, str, float, float, DateType, float, str]] = set()

    for row in rows:
        identity = _transaction_identity(row)
        if identity in seen:
            row.add_error("duplicate transaction in CSV")
            continue
        seen.add(identity)

        (
            ticker,
            asset_type,
            operation,
            quantity,
            price,
            parsed_date,
            fees,
            currency,
        ) = identity
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
            row.add_error("duplicate transaction already exists")


async def _validate_writer_preflight(
    rows: list[CSVRow],
    db: AsyncSession,
) -> None:
    """Antecipa blockers do writer canonico no dry-run, sem escrever no banco."""
    for row in rows:
        if row.errors or row.warnings:
            continue

        ticker = row.data.get("ticker", "").strip().upper()
        asset_type = row.data.get("asset_type", "").strip().upper()
        if asset_type != AssetType.CRIPTO.value:
            continue

        try:
            await require_catalog_crypto_asset(db, ticker)
        except CryptoTransactionEligibilityError as exc:
            row.add_error(str(exc))

    await _validate_persisted_price_history_preflight(rows, db)


async def _validate_persisted_price_history_preflight(
    rows: list[CSVRow],
    db: AsyncSession,
) -> None:
    """Bloqueia ativos de mercado sem catálogo e histórico persistido."""
    requirements = {
        (
            row.data.get("ticker", "").strip().upper(),
            row.data.get("asset_type", "").strip().upper(),
        )
        for row in rows
        if not row.errors
        and not row.warnings
        and row.data.get("asset_type", "").strip().upper() in PRICE_HISTORY_REQUIRED_TYPES
    }
    if not requirements:
        return

    assets_result = await db.execute(
        select(
            Asset.ticker,
            Asset.asset_type,
            Asset.last_price,
            func.count(AssetPrice.id).label("price_rows"),
        )
        .outerjoin(AssetPrice, AssetPrice.asset_id == Asset.id)
        .where(
            func.upper(Asset.ticker).in_([ticker for ticker, _ in requirements]),
            Asset.asset_type.in_([asset_type for _, asset_type in requirements]),
        )
        .group_by(Asset.id, Asset.ticker, Asset.asset_type, Asset.last_price)
    )
    coverage = {
        (str(row.ticker).strip().upper(), str(row.asset_type).strip().upper()): {
            "last_price": row.last_price,
            "price_rows": int(row.price_rows or 0),
        }
        for row in assets_result.all()
    }

    for row in rows:
        if row.errors or row.warnings:
            continue
        ticker = row.data.get("ticker", "").strip().upper()
        asset_type = row.data.get("asset_type", "").strip().upper()
        if asset_type not in PRICE_HISTORY_REQUIRED_TYPES:
            continue
        item = coverage.get((ticker, asset_type))
        if item is None:
            row.add_error(
                f"{ticker} {asset_type} nao elegivel para importacao: ativo nao esta no catalogo persistido"
            )
            continue
        if item["last_price"] is None or item["price_rows"] <= 0:
            row.add_error(
                f"{ticker} {asset_type} nao elegivel para importacao: historico de precos persistido indisponivel"
            )


async def parse_csv_content(
    content: str,
    portfolio_id: int,
    db: AsyncSession,
) -> tuple[list[CSVRow], list[str]]:
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

        missing_headers = set(CSV_REQUIRED_HEADERS) - set(csv_reader.fieldnames)
        if missing_headers:
            global_errors.append(f"Missing required headers: {', '.join(missing_headers)}")
            return rows, global_errors

        for row_num, raw_row in enumerate(csv_reader, start=2):
            csv_row = CSVRow(row_num, raw_row)

            if not any(raw_row.values()):
                csv_row.add_warning("Empty row, skipping")
                rows.append(csv_row)
                continue

            asset_type = raw_row.get("asset_type", "").strip().upper()
            raw_ticker = raw_row.get("ticker", "")
            ticker = await _resolve_csv_ticker(raw_ticker, asset_type, db)
            raw_row["ticker"] = ticker or raw_ticker.strip().upper()
            raw_row["asset_type"] = asset_type
            operation = raw_row.get("operation", "").strip().lower()
            raw_row["operation"] = operation
            quantity_str = raw_row.get("quantity", "").strip()
            price_str = raw_row.get("price", "").strip()
            date_str = raw_row.get("date", "").strip()
            fees_str = raw_row.get("fees", "0").strip()
            currency = raw_row.get("currency", "BRL").strip().upper()
            raw_row["currency"] = currency
            _parse_fixed_income_contract_row(csv_row)
            if not raw_ticker.strip():
                csv_row.add_error("ticker is required")
            elif asset_type == AssetType.TESOURO_DIRETO.value and ticker is None:
                csv_row.add_error(
                    "ticker de Tesouro Direto nao encontrado no catalogo persistido"
                )

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
        global_errors.append(f"Error parsing CSV: {e!s}")
        logger.error("CSV parse error: %s", sanitize_log_value(e))

    _validate_fixed_income_contract_groups(rows)
    return rows, global_errors


def _parse_optional_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized in {"true", "1", "yes", "sim"}:
        return True
    if normalized in {"false", "0", "no", "nao", "não"}:
        return False
    raise ValueError("fixed_income_tax_exempt must be true or false")


def _parse_fixed_income_contract_row(row: CSVRow) -> None:
    data = row.data
    key = (data.get("fixed_income_contract_key") or "").strip()
    raw_fields = {
        "product_type": (data.get("fixed_income_product_type") or "").strip(),
        "display_name": (data.get("fixed_income_display_name") or "").strip(),
        "issuer": (data.get("fixed_income_issuer") or "").strip(),
        "indexer": (data.get("fixed_income_indexer") or "").strip(),
        "rate_value": (data.get("fixed_income_rate_value") or "").strip(),
        "rate_unit": (data.get("fixed_income_rate_unit") or "").strip(),
        "maturity_date": (data.get("fixed_income_maturity_date") or "").strip(),
        "liquidity_type": (data.get("fixed_income_liquidity_type") or "").strip(),
        "grace_period_end": (data.get("fixed_income_grace_period_end") or "").strip(),
        "tax_exempt": (data.get("fixed_income_tax_exempt") or "").strip(),
        "currency": (data.get("fixed_income_currency") or "").strip(),
    }
    has_metadata = any(raw_fields.values())
    data["fixed_income_contract_key"] = key or None
    data["fixed_income_contract"] = None

    if not key and not has_metadata:
        return
    if not key:
        row.add_error("fixed_income_contract_key is required when contract metadata is present")
        return
    if not has_metadata:
        row.add_error("fixed income contract metadata is required for the provided key")
        return
    if data.get("asset_type") != AssetType.RENDA_FIXA.value:
        row.add_error("fixed income contract metadata can only be used with RENDA_FIXA")
        return

    payload: dict[str, Any] = {}
    if raw_fields["display_name"]:
        payload["display_name"] = raw_fields["display_name"]
    if raw_fields["product_type"]:
        payload["product_type"] = raw_fields["product_type"].upper()
    if raw_fields["issuer"]:
        payload["issuer"] = raw_fields["issuer"]
    if raw_fields["indexer"]:
        payload["indexer"] = raw_fields["indexer"].upper()
    if raw_fields["rate_value"]:
        try:
            payload["rate_value"] = Decimal(raw_fields["rate_value"])
        except InvalidOperation:
            row.add_error("fixed_income_rate_value must be a valid decimal number")
            return
    if raw_fields["rate_unit"]:
        payload["rate_unit"] = raw_fields["rate_unit"].upper()
    for field in ("maturity_date", "grace_period_end"):
        if raw_fields[field]:
            try:
                payload[field] = _parse_date(raw_fields[field])
            except ValueError:
                row.add_error(f"{field} must use YYYY-MM-DD")
                return
    if raw_fields["liquidity_type"]:
        payload["liquidity_type"] = raw_fields["liquidity_type"].upper()
    if raw_fields["tax_exempt"]:
        try:
            payload["tax_exempt"] = _parse_optional_bool(raw_fields["tax_exempt"])
        except ValueError as exc:
            row.add_error(str(exc))
            return
    if raw_fields["currency"]:
        payload["currency"] = raw_fields["currency"].upper()

    try:
        data["fixed_income_contract"] = FixedIncomeContractCreate(**payload)
    except ValidationError as exc:
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"])
            row.add_error(f"Invalid fixed income contract {field}: {error['msg']}")


def _validate_fixed_income_contract_groups(rows: list[CSVRow]) -> None:
    contracts: dict[str, tuple[Any, int]] = {}
    for row in rows:
        key = row.data.get("fixed_income_contract_key")
        contract = row.data.get("fixed_income_contract")
        if not key or contract is None or row.errors:
            continue
        terms = contract.model_dump(mode="python")
        previous = contracts.get(key)
        if previous is None:
            contracts[key] = (terms, row.row_num)
        elif previous[0] != terms:
            row.add_error(
                f"fixed income contract key '{key}' has inconsistent metadata"
            )


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
) -> dict[str, Any]:
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
    if not global_errors and not any(row.errors or row.warnings for row in rows):
        await _validate_duplicate_transactions(rows, portfolio_id, db)
    if not global_errors and not any(row.errors or row.warnings for row in rows):
        await _validate_writer_preflight(rows, db)
    result["global_errors"] = global_errors

    duplicate_only = (
        bool(rows)
        and not global_errors
        and all(
            row.errors == ["duplicate transaction already exists"] and not row.warnings
            for row in rows
        )
    )
    if duplicate_only:
        result["success"] = True
        result["skipped_count"] = len(rows)
        result["rows"] = [
            {
                "row_num": row.row_num,
                "errors": [],
                "warnings": ["duplicate transaction skipped"],
                "status": "skipped",
                "ticker": (row.data.get("ticker") or "").strip().upper() or None,
                "operation": (row.data.get("operation") or "").strip().lower() or None,
                "quantity": _safe_float(row.data.get("quantity")),
            }
            for row in rows
        ]
        return result

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
    fixed_income_contract_ids: dict[str, int] = {}
    creation_failed = False

    for csv_row in rows:
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

            transaction = await add_transaction_record(
                db,
                portfolio_id=portfolio_id,
                payload=TransactionCreate(
                    ticker=ticker,
                    asset_type=asset_type,
                    operation=operation,
                    quantity=quantity,
                    price=price,
                    fees=fees,
                    date=parsed_date,
                    currency=currency,
                    notes=notes if notes else None,
                    fixed_income_contract_id=(
                        fixed_income_contract_ids.get(
                            csv_row.data.get("fixed_income_contract_key") or ""
                        )
                    ),
                    fixed_income_contract=(
                        None
                        if csv_row.data.get("fixed_income_contract_key")
                        in fixed_income_contract_ids
                        else csv_row.data.get("fixed_income_contract")
                    ),
                ),
                flush=True,
            )
            contract_key = csv_row.data.get("fixed_income_contract_key")
            if contract_key and contract_key not in fixed_income_contract_ids:
                contract_id = transaction.fixed_income_contract_id
                if contract_id is None:
                    raise TransactionWriteError(
                        "Contrato de Renda Fixa nao foi associado ao lancamento"
                    )
                fixed_income_contract_ids[contract_key] = contract_id
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

        except (TransactionWriteError, ValueError) as e:
            creation_failed = True
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

    if creation_failed:
        await db.rollback()
        result["success"] = False
        result["imported_count"] = 0
        for row in result["rows"]:
            if row.get("status") == "imported":
                row["status"] = "skipped"
                row["warnings"] = ["transaction rolled back because batch has errors"]
        return result

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
            result["global_errors"].append(f"Database error: {e!s}")
    else:
        result["success"] = result["error_count"] == 0

    return result


async def export_transactions_csv(db: AsyncSession, portfolio_id: int) -> str:
    """Export one portfolio's ledger and linked contract metadata as CSV."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_TEMPLATE_HEADERS)
    writer.writeheader()
    result = await db.execute(
        select(Transaction, FixedIncomeContract)
        .outerjoin(Transaction.fixed_income_contract)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date, Transaction.id)
    )

    contract_keys: dict[int, str] = {}
    for transaction, contract in result.all():
        row: dict[str, Any] = {
            "ticker": transaction.ticker,
            "asset_type": transaction.asset_type,
            "operation": (
                transaction.operation.value
                if isinstance(transaction.operation, OperationType)
                else str(transaction.operation)
            ),
            "quantity": str(transaction.quantity),
            "price": str(transaction.price),
            "date": transaction.date.isoformat(),
            "fees": str(transaction.fees),
            "currency": transaction.currency,
            "notes": transaction.notes or "",
        }
        for field in CSV_FIXED_INCOME_FIELDS:
            row[field] = ""

        if contract is not None:
            key = contract_keys.setdefault(
                contract.id, f"FIXED_INCOME_CONTRACT_{len(contract_keys) + 1}"
            )
            row.update({
                "fixed_income_contract_key": key,
                "fixed_income_product_type": contract.product_type,
                "fixed_income_display_name": contract.display_name,
                "fixed_income_issuer": contract.issuer or "",
                "fixed_income_indexer": contract.indexer or "",
                "fixed_income_rate_value": (
                    str(contract.rate_value) if contract.rate_value is not None else ""
                ),
                "fixed_income_rate_unit": contract.rate_unit or "",
                "fixed_income_maturity_date": (
                    contract.maturity_date.isoformat()
                    if contract.maturity_date is not None
                    else ""
                ),
                "fixed_income_liquidity_type": contract.liquidity_type or "",
                "fixed_income_grace_period_end": (
                    contract.grace_period_end.isoformat()
                    if contract.grace_period_end is not None
                    else ""
                ),
                "fixed_income_tax_exempt": (
                    "true"
                    if contract.tax_exempt is True
                    else "false"
                    if contract.tax_exempt is False
                    else ""
                ),
                "fixed_income_currency": contract.currency,
            })
        writer.writerow(row)
    return output.getvalue()
