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
    execute_result.scalar_one.side_effect = [None, None, None]
    db.execute.return_value = execute_result
    
    result = await get_summary(db, portfolio_id=1)
    
    assert result["total_recebido"] == 0.0
    assert result["total_a_receber"] == 0.0
    assert result["total_12m"] == 0.0
    assert result["media_mensal_12m"] == 0.0


@pytest.mark.asyncio
async def test_get_summary_with_dividends():
    db = AsyncMock(spec=AsyncSession)
    
    execute_result = MagicMock()
    execute_result.scalar_one.side_effect = [1500.0, 500.0, 800.0]
    db.execute.return_value = execute_result
    
    result = await get_summary(db, portfolio_id=1)
    
    assert result["total_recebido"] == 1500.0
    assert result["total_a_receber"] == 500.0
    assert result["total_12m"] == 800.0
    assert result["media_mensal_12m"] == round(800.0 / 12, 2)


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
    mock_row.ex_date = date(2024, 1, 15)
    mock_row.payment_date = date(2024, 1, 20)
    mock_row.value_per_unit = 2.5
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
    mock_row.ex_date = date(2024, 6, 15)
    mock_row.payment_date = date(2024, 6, 20)
    mock_row.value_per_unit = 1.5
    mock_row.quantity = 50.0
    mock_row.total_value = 75.0
    mock_row.net_value = 75.0
    mock_row.status = DividendStatus.A_RECEBER
    
    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = [mock_row]
    
    db.execute.side_effect = [count_result, fetch_result]
    
    result = await list_items(
        db,
        portfolio_id=1,
        status=DividendStatus.A_RECEBER,
        year=2024,
        asset_type="STOCK",
    )
    
    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["status"] == DividendStatus.A_RECEBER


@pytest.mark.asyncio
async def test_get_monthly_history_empty():
    db = AsyncMock(spec=AsyncSession)
    
    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = []
    db.execute.return_value = fetch_result
    
    result = await get_monthly_history(db, portfolio_id=1)
    
    assert result == []


@pytest.mark.asyncio
async def test_get_monthly_history_with_data():
    db = AsyncMock(spec=AsyncSession)
    
    mock_row1 = MagicMock()
    mock_row1.year = 2024.0
    mock_row1.month = 1.0
    mock_row1.total = 500.0
    
    mock_row2 = MagicMock()
    mock_row2.year = 2024.0
    mock_row2.month = 2.0
    mock_row2.total = 600.0
    
    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = [mock_row1, mock_row2]
    db.execute.return_value = fetch_result
    
    result = await get_monthly_history(db, portfolio_id=1)
    
    assert len(result) == 1
    assert result[0]["year"] == 2024
    assert result[0]["total"] == 1100.0
    assert result[0]["media"] == 550.0


@pytest.mark.asyncio
async def test_get_monthly_history_multiple_years():
    db = AsyncMock(spec=AsyncSession)
    
    mock_rows = [
        MagicMock(year=2023.0, month=12.0, total=200.0),
        MagicMock(year=2024.0, month=1.0, total=500.0),
        MagicMock(year=2024.0, month=2.0, total=600.0),
    ]
    
    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = mock_rows
    db.execute.return_value = fetch_result
    
    result = await get_monthly_history(db, portfolio_id=1)
    
    assert len(result) == 2
    assert result[0]["year"] == 2024
    assert result[1]["year"] == 2023


@pytest.mark.asyncio
async def test_get_distribution_empty():
    db = AsyncMock(spec=AsyncSession)
    
    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = []
    db.execute.return_value = fetch_result
    
    result = await get_distribution(db, portfolio_id=1, months=12)
    
    assert result == []


@pytest.mark.asyncio
async def test_get_distribution_single_asset():
    db = AsyncMock(spec=AsyncSession)
    
    mock_row = MagicMock()
    mock_row.ticker = "VALE3"
    mock_row.asset_type = "STOCK"
    mock_row.total = 1000.0
    
    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = [mock_row]
    db.execute.return_value = fetch_result
    
    result = await get_distribution(db, portfolio_id=1, months=12)
    
    assert len(result) == 1
    assert result[0]["ticker"] == "VALE3"
    assert result[0]["asset_type"] == "STOCK"
    assert result[0]["total"] == 1000.0
    assert result[0]["percentage"] == 100.0


@pytest.mark.asyncio
async def test_get_distribution_multiple_assets():
    db = AsyncMock(spec=AsyncSession)
    
    mock_row1 = MagicMock()
    mock_row1.ticker = "VALE3"
    mock_row1.asset_type = "STOCK"
    mock_row1.total = 600.0
    
    mock_row2 = MagicMock()
    mock_row2.ticker = "PETR4"
    mock_row2.asset_type = "STOCK"
    mock_row2.total = 400.0
    
    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = [mock_row1, mock_row2]
    db.execute.return_value = fetch_result
    
    result = await get_distribution(db, portfolio_id=1, months=12)
    
    assert len(result) == 2
    assert result[0]["ticker"] == "VALE3"
    assert result[0]["percentage"] == 60.0
    assert result[1]["ticker"] == "PETR4"
    assert result[1]["percentage"] == 40.0


@pytest.mark.asyncio
async def test_get_distribution_different_months():
    db = AsyncMock(spec=AsyncSession)
    
    mock_row = MagicMock()
    mock_row.ticker = "BBAS3"
    mock_row.asset_type = "STOCK"
    mock_row.total = 800.0
    
    fetch_result = MagicMock()
    fetch_result.fetchall.return_value = [mock_row]
    db.execute.return_value = fetch_result
    
    result = await get_distribution(db, portfolio_id=1, months=6)
    
    assert len(result) == 1
    assert result[0]["total"] == 800.0
