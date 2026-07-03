"""Testes para csv_import_service — importacao de transacoes via CSV."""
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, OperationType
from app.models.asset import Asset, AssetType
from app.models.portfolio import Portfolio
from app.services.csv_import_service import (
    generate_csv_template,
    parse_csv_content,
    import_csv_transactions,
    _parse_date,
    CSVRow,
)


class TestGenerateCSVTemplate:

    def test_template_has_all_headers(self):
        template = generate_csv_template()
        assert "ticker" in template
        assert "asset_type" in template
        assert "operation" in template
        assert "quantity" in template
        assert "price" in template
        assert "date" in template
        assert "fees" in template
        assert "currency" in template
        assert "notes" in template

    def test_template_has_example_rows(self):
        template = generate_csv_template()
        assert "PETR4" in template
        assert "VALE3" in template
        assert "IVVB11" in template
        assert "buy" in template

    def test_template_is_valid_csv(self):
        import csv
        import io
        template = generate_csv_template()
        reader = csv.DictReader(io.StringIO(template))
        rows = list(reader)
        assert len(rows) == 3


class TestCSVRowClass:

    def test_csv_row_initialization(self):
        data = {"ticker": "PETR4", "quantity": "100"}
        row = CSVRow(2, data)
        assert row.row_num == 2
        assert row.data == data
        assert row.errors == []
        assert row.warnings == []

    def test_add_error(self):
        row = CSVRow(2, {})
        row.add_error("Test error")
        assert "Test error" in row.errors

    def test_add_warning(self):
        row = CSVRow(2, {})
        row.add_warning("Test warning")
        assert "Test warning" in row.warnings

    def test_is_valid_no_errors(self):
        row = CSVRow(2, {})
        assert row.is_valid() is True

    def test_is_valid_with_errors(self):
        row = CSVRow(2, {})
        row.add_error("Error")
        assert row.is_valid() is False

    def test_is_valid_with_only_warnings(self):
        row = CSVRow(2, {})
        row.add_warning("Warning")
        assert row.is_valid() is True


class TestParseDate:

    def test_parse_date_iso_format(self):
        result = _parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_date_slash_format(self):
        result = _parse_date("15/01/2024")
        assert result == date(2024, 1, 15)

    def test_parse_date_dash_format(self):
        result = _parse_date("15-01-2024")
        assert result == date(2024, 1, 15)

    def test_parse_date_iso_slash_format(self):
        result = _parse_date("2024/01/15")
        assert result == date(2024, 1, 15)

    def test_parse_date_invalid_format(self):
        with pytest.raises(ValueError):
            _parse_date("invalid-date")

    def test_parse_date_invalid_day(self):
        with pytest.raises(ValueError):
            _parse_date("2024-13-01")


@pytest.mark.asyncio
class TestParseCSVContent:

    async def test_parse_valid_csv(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,Compra inicial
VALE3,ACAO,buy,50,80.00,2024-02-20,5.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(global_errors) == 0
        assert len(rows) == 2
        assert rows[0].is_valid()
        assert rows[1].is_valid()

    async def test_parse_csv_missing_headers(self):
        content = """ticker,quantity,price
PETR4,100,25.50"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(global_errors) > 0
        assert "Missing required headers" in global_errors[0]

    async def test_parse_csv_missing_ticker(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "ticker is required" in rows[0].errors

    async def test_parse_csv_invalid_asset_type(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,INVALID_TYPE,buy,100,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "asset_type" in rows[0].errors[0]

    async def test_parse_csv_invalid_operation(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,invalid_op,100,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "operation" in rows[0].errors[0]

    async def test_parse_csv_invalid_quantity(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,invalid,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "quantity" in rows[0].errors[0]

    async def test_parse_csv_zero_quantity(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,0,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "quantity must be positive" in rows[0].errors

    async def test_parse_csv_invalid_price(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,invalid,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "price" in rows[0].errors[0]

    async def test_parse_csv_zero_price(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,0,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "price must be positive" in rows[0].errors

    async def test_parse_csv_invalid_date(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,invalid-date,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "date" in rows[0].errors[0]

    async def test_parse_csv_future_date_warning(self):
        future_date = "2099-12-31"
        content = f"""ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,{future_date},10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "future" in rows[0].warnings[0].lower()

    async def test_parse_csv_negative_fees(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,-10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "fees cannot be negative" in rows[0].errors

    async def test_parse_csv_invalid_fees(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,invalid,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 1
        assert "fees" in rows[0].errors[0]

    async def test_parse_csv_empty_row(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,
,,,,,,,,
VALE3,ACAO,buy,50,80.00,2024-02-20,5.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(rows) == 3
        assert "Empty row" in rows[1].warnings[0]

    async def test_parse_csv_empty_file(self):
        content = ""

        db = AsyncMock(spec=AsyncSession)
        rows, global_errors = await parse_csv_content(content, 1, db)

        assert len(global_errors) > 0


@pytest.mark.asyncio
class TestImportCSVTransactions:

    async def test_import_valid_transactions(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,Compra inicial"""

        db = AsyncMock(spec=AsyncSession)
        
        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 1
        
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)
        
        asset_result = MagicMock()
        asset_result.scalar_one_or_none = MagicMock(return_value=None)
        
        db.execute = AsyncMock(side_effect=[portfolio_result, asset_result])
        db.commit = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        
        with patch('app.services.csv_import_service.invalidate_portfolio_cache', new_callable=AsyncMock):
            result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is True
        assert result["imported_count"] == 1

    async def test_import_portfolio_not_found(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=None)
        
        db.execute = AsyncMock(return_value=portfolio_result)

        result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is False
        assert "not found" in result["global_errors"][0].lower()

    async def test_import_unauthorized_user(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        
        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 999
        
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)
        
        db.execute = AsyncMock(return_value=portfolio_result)

        result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is False
        assert "Unauthorized" in result["global_errors"][0]

    async def test_import_with_validation_errors(self):
        content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,invalid,25.50,2024-01-15,10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        
        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 1
        
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)
        
        db.execute = AsyncMock(return_value=portfolio_result)

        result = await import_csv_transactions(content, 1, 1, db)

        assert result["success"] is False
        assert result["error_count"] > 0

    async def test_import_with_warnings_skipped(self):
        future_date = "2099-12-31"
        content = f"""ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,100,25.50,{future_date},10.00,BRL,"""

        db = AsyncMock(spec=AsyncSession)
        
        portfolio = MagicMock(spec=Portfolio)
        portfolio.user_id = 1
        
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none = MagicMock(return_value=portfolio)
        
        db.execute = AsyncMock(return_value=portfolio_result)

        result = await import_csv_transactions(content, 1, 1, db)

        assert result["skipped_count"] == 1
