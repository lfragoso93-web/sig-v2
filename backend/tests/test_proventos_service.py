import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.proventos_service import (
    get_summary,
    list_items,
    get_monthly_history,
    get_distribution,
)
from app.models.dividend import DividendStatus


@pytest.mark.asyncio
async def test_get_summary_no_dividends():
    db = AsyncMock(spec=AsyncSession)

    execute_result = MagicMock()
    execute_result.scalar_one.side_effect = [None, None, None, None, None, 0]
    db.execute.return_value = execute_result

    result = await get_summary(db, portfolio_id=1)

    assert result["total_recebido"] == 0.0
    assert result["total_liquido_recebido"] == 0.0
    assert result["total_bruto_recebido"] == 0.0
    assert result["total_a_receber"] == 0.0
    assert result["total_liquido_a_receber"] == 0.0
    assert result["total_bruto_a_receber"] == 0.0
    assert result["total_12m"] == 0.0
    assert result["media_mensal_12m"] == 0.0
    assert result["eventos_nao_cash"] == 0


@pytest.mark.asyncio
async def test_get_summary_with_dividends():
    db = AsyncMock(spec=AsyncSession)

    execute_result = MagicMock()
    execute_result.scalar_one.side_effect = [1500.0, 1600.0, 500.0, 550.0, 800.0, 2]
    db.execute.return_value = execute_result

    result = await get_summary(db, portfolio_id=1)

    assert result["total_recebido"] == 1500.0
    assert result["total_liquido_recebido"] == 1500.0
    assert result["total_bruto_recebido"] == 1600.0
    assert result["total_a_receber"] == 500.0
    assert result["total_liquido_a_receber"] == 500.0
    assert result["total_bruto_a_receber"] == 550.0
    assert result["total_12m"] == 800.0
    assert result["media_mensal_12m"] == round(800.0 / 12, 2)
    assert result["eventos_nao_cash"] == 2


@pytest.mark.asyncio
async def test_list_items_empty():
    db = AsyncMock(spec=AsyncSession)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = []

    db.execute.side_effect = [count_result, fetch_result]

    result = await list_items(db, portfolio_id=1)

    assert result["total"] == 0
    assert result["page"] == 1
    assert result["page_size"] == 50
    assert result["items"] == []


@pytest.mark.asyncio
async def test_list_items_with_data():
    db = AsyncMock(spec=AsyncSession)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 2

    mock_row = MagicMock()
    mock_row.id = 1
    mock_row.ticker = "VALE3"
    mock_row.asset_type = "STOCK"
    mock_row.dividend_type = "Dividendo"
    mock_row.record_date = date(2024, 1, 10)
    mock_row.ex_date = date(2024, 1, 15)
    mock_row.payment_date = date(2024, 1, 20)
    mock_row.approved_on = None
    mock_row.value_per_unit = 2.5
    mock_row.gross_value_per_unit = None
    mock_row.factor = None
    mock_row.complete_factor = None
    mock_row.isin_code = None
    mock_row.asset_issued = None
    mock_row.related_to = None
    mock_row.remarks = None
    mock_row.quantity = 100.0
    mock_row.total_value = 250.0
    mock_row.net_value = 250.0
    mock_row.status = DividendStatus.RECEBIDO

    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = [mock_row]

    db.execute.side_effect = [count_result, fetch_result]

    result = await list_items(db, portfolio_id=1, page=1, page_size=50)

    assert result["total"] == 2
    assert len(result["items"]) == 1
    assert result["items"][0]["ticker"] == "VALE3"
    assert result["items"][0]["net_value"] == 250.0


@pytest.mark.asyncio
async def test_list_items_with_filters():
    db = AsyncMock(spec=AsyncSession)

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    mock_row = MagicMock()
    mock_row.id = 1
    mock_row.ticker = "PETR4"
    mock_row.asset_type = "STOCK"
    mock_row.dividend_type = "Dividendo"
    mock_row.record_date = date(2024, 6, 10)
    mock_row.ex_date = date(2024, 6, 15)
    mock_row.payment_date = date(2024, 6, 20)
    mock_row.approved_on = None
    mock_row.value_per_unit = 1.5
    mock_row.gross_value_per_unit = None
    mock_row.factor = None
    mock_row.complete_factor = None
    mock_row.isin_code = None
    mock_row.asset_issued = None
    mock_row.related_to = None
    mock_row.remarks = None
    mock_row.quantity = 50.0
    mock_row.total_value = 75.0
    mock_row.net_value = 75.0
    mock_row.status = DividendStatus.A_RECEBER

    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = [mock_row]

    db.execute.side_effect = [count_result, fetch_result]

    result = await list_items(db, portfolio_id=1, status=DividendStatus.A_RECEBER, page=1, page_size=50)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["ticker"] == "PETR4"
    assert result["items"][0]["status"] == DividendStatus.A_RECEBER


@pytest.mark.asyncio
async def test_get_monthly_history_empty():
    db = AsyncMock(spec=AsyncSession)

    execute_result = MagicMock()
    execute_result.fetchall.return_value = []
    db.execute.return_value = execute_result

    result = await get_monthly_history(db, portfolio_id=1)

    assert result == []


@pytest.mark.asyncio
async def test_get_monthly_history_with_data():
    db = AsyncMock(spec=AsyncSession)

    mock_row = MagicMock()
    mock_row.year = 2024
    mock_row.month = 6
    mock_row.total = 1500.0

    execute_result = MagicMock()
    execute_result.fetchall.return_value = [mock_row]
    db.execute.return_value = execute_result

    result = await get_monthly_history(db, portfolio_id=1)

    assert len(result) == 1
    assert result[0]["year"] == 2024
    assert result[0]["months"][5] == 1500.0
    assert result[0]["total"] == 1500.0
    assert result[0]["media"] == 1500.0


@pytest.mark.asyncio
async def test_get_monthly_history_multiple_years():
    db = AsyncMock(spec=AsyncSession)

    row1 = MagicMock()
    row1.year = 2024
    row1.month = 6
    row1.total = 1000.0

    row2 = MagicMock()
    row2.year = 2023
    row2.month = 12
    row2.total = 500.0

    execute_result = MagicMock()
    execute_result.fetchall.return_value = [row2, row1]
    db.execute.return_value = execute_result

    result = await get_monthly_history(db, portfolio_id=1)

    assert len(result) == 2
    assert result[0]["year"] == 2024
    assert result[1]["year"] == 2023


@pytest.mark.asyncio
async def test_get_distribution_empty():
    db = AsyncMock(spec=AsyncSession)

    execute_result = MagicMock()
    execute_result.fetchall.return_value = []
    db.execute.return_value = execute_result

    result = await get_distribution(db, portfolio_id=1)

    assert result == []


@pytest.mark.asyncio
async def test_get_distribution_single_asset():
    db = AsyncMock(spec=AsyncSession)

    mock_row = MagicMock()
    mock_row.ticker = "VALE3"
    mock_row.asset_type = "STOCK"
    mock_row.total = 1000.0

    execute_result = MagicMock()
    execute_result.fetchall.return_value = [mock_row]
    db.execute.return_value = execute_result

    result = await get_distribution(db, portfolio_id=1)

    assert len(result) == 1
    assert result[0]["ticker"] == "VALE3"
    assert result[0]["total"] == 1000.0
    assert result[0]["percentage"] == 100.0


@pytest.mark.asyncio
async def test_get_distribution_multiple_assets():
    db = AsyncMock(spec=AsyncSession)

    row1 = MagicMock()
    row1.ticker = "VALE3"
    row1.asset_type = "STOCK"
    row1.total = 1000.0

    row2 = MagicMock()
    row2.ticker = "PETR4"
    row2.asset_type = "STOCK"
    row2.total = 500.0

    execute_result = MagicMock()
    execute_result.fetchall.return_value = [row1, row2]
    db.execute.return_value = execute_result

    result = await get_distribution(db, portfolio_id=1)

    assert len(result) == 2
    assert result[0]["percentage"] == round(1000.0 / 1500.0 * 100, 2)
    assert result[1]["percentage"] == round(500.0 / 1500.0 * 100, 2)


@pytest.mark.asyncio
async def test_get_distribution_different_months():
    db = AsyncMock(spec=AsyncSession)

    mock_row = MagicMock()
    mock_row.ticker = "VALE3"
    mock_row.asset_type = "STOCK"
    mock_row.total = 1000.0

    execute_result = MagicMock()
    execute_result.fetchall.return_value = [mock_row]
    db.execute.return_value = execute_result

    result = await get_distribution(db, portfolio_id=1, months=6)

    assert len(result) == 1
    assert result[0]["total"] == 1000.0
