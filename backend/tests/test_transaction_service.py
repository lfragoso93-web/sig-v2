import pytest
from datetime import date
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.services.transaction_service import (
    list_transactions_paginated,
)
from app.models.transaction import OperationType


@pytest.mark.asyncio
async def test_list_transactions_paginated_empty():
    db = AsyncMock(spec=AsyncSession)
    
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    
    fetch_result = MagicMock()
    fetch_result.scalars().all.return_value = []
    
    db.execute.side_effect = [count_result, fetch_result]
    
    result = await list_transactions_paginated(db, portfolio_id=1)
    
    assert result["total"] == 0
    assert result["items"] == []
    assert result["page"] == 1
    assert result["page_size"] == 50


@pytest.mark.asyncio
async def test_list_transactions_paginated_with_data():
    db = AsyncMock(spec=AsyncSession)
    
    mock_tx = MagicMock()
    mock_tx.id = 1
    mock_tx.ticker = "VALE3"
    mock_tx.operation = OperationType.buy
    mock_tx.quantity = 100.0
    mock_tx.price = 50.0
    mock_tx.date = date(2024, 1, 15)
    mock_tx.asset_type = "ACAO"
    mock_tx.fees = 10.0
    
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    
    fetch_result = MagicMock()
    fetch_result.scalars().all.return_value = [mock_tx]
    
    db.execute.side_effect = [count_result, fetch_result]
    
    result = await list_transactions_paginated(db, portfolio_id=1)
    
    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0].ticker == "VALE3"


@pytest.mark.asyncio
async def test_list_transactions_paginated_with_filters():
    db = AsyncMock(spec=AsyncSession)
    
    mock_tx = MagicMock()
    mock_tx.id = 1
    mock_tx.ticker = "PETR4"
    mock_tx.operation = OperationType.buy
    mock_tx.quantity = 200.0
    mock_tx.price = 30.0
    mock_tx.date = date(2024, 6, 15)
    
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    
    fetch_result = MagicMock()
    fetch_result.scalars().all.return_value = [mock_tx]
    
    db.execute.side_effect = [count_result, fetch_result]
    
    result = await list_transactions_paginated(
        db,
        portfolio_id=1,
        ticker="PETR4",
        operation="buy",
        date_from=date(2024, 1, 1),
    )
    
    assert result["total"] == 1
    assert len(result["items"]) == 1


@pytest.mark.asyncio
async def test_list_transactions_paginated_pagination():
    db = AsyncMock(spec=AsyncSession)
    
    mock_tx = MagicMock()
    mock_tx.id = 1
    
    count_result = MagicMock()
    count_result.scalar_one.return_value = 100
    
    fetch_result = MagicMock()
    fetch_result.scalars().all.return_value = [mock_tx]
    
    db.execute.side_effect = [count_result, fetch_result]
    
    result = await list_transactions_paginated(
        db,
        portfolio_id=1,
        page=2,
        page_size=25,
    )
    
    assert result["total"] == 100
    assert result["page"] == 2
    assert result["page_size"] == 25


@pytest.mark.asyncio
async def test_calc_average_price_single_buy():
    from app.services.transaction_service import _calc_average_price
    
    db = MagicMock(spec=Session)
    
    mock_tx = MagicMock()
    mock_tx.operation = OperationType.buy
    mock_tx.quantity = 100.0
    mock_tx.price = 50.0
    
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_tx]
    db.query.return_value = mock_query
    
    avg_price = _calc_average_price(db, portfolio_id=1, ticker="VALE3")
    
    assert avg_price == 50.0


@pytest.mark.asyncio
async def test_calc_average_price_multiple_buys():
    from app.services.transaction_service import _calc_average_price
    
    db = MagicMock(spec=Session)
    
    mock_tx1 = MagicMock()
    mock_tx1.operation = OperationType.buy
    mock_tx1.quantity = 100.0
    mock_tx1.price = 50.0
    
    mock_tx2 = MagicMock()
    mock_tx2.operation = OperationType.buy
    mock_tx2.quantity = 100.0
    mock_tx2.price = 60.0
    
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_tx1, mock_tx2]
    db.query.return_value = mock_query
    
    avg_price = _calc_average_price(db, portfolio_id=1, ticker="VALE3")
    
    assert avg_price == 55.0


@pytest.mark.asyncio
async def test_calc_average_price_buy_and_sell():
    from app.services.transaction_service import _calc_average_price
    
    db = MagicMock(spec=Session)
    
    mock_buy = MagicMock()
    mock_buy.operation = OperationType.buy
    mock_buy.quantity = 100.0
    mock_buy.price = 50.0
    
    mock_sell = MagicMock()
    mock_sell.operation = OperationType.sell
    mock_sell.quantity = 30.0
    mock_sell.price = 60.0
    
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_buy, mock_sell]
    db.query.return_value = mock_query
    
    avg_price = _calc_average_price(db, portfolio_id=1, ticker="VALE3")
    
    assert avg_price == 50.0


@pytest.mark.asyncio
async def test_calc_average_price_all_sold():
    from app.services.transaction_service import _calc_average_price
    
    db = MagicMock(spec=Session)
    
    mock_buy = MagicMock()
    mock_buy.operation = OperationType.buy
    mock_buy.quantity = 100.0
    mock_buy.price = 50.0
    
    mock_sell = MagicMock()
    mock_sell.operation = OperationType.sell
    mock_sell.quantity = 100.0
    mock_sell.price = 60.0
    
    mock_query = MagicMock()
    mock_query.filter.return_value.order_by.return_value.all.return_value = [mock_buy, mock_sell]
    db.query.return_value = mock_query
    
    avg_price = _calc_average_price(db, portfolio_id=1, ticker="VALE3")
    
    assert avg_price == 0.0


@pytest.mark.asyncio
async def test_calc_current_quantity_single_buy():
    from app.services.transaction_service import _calc_current_quantity
    
    db = MagicMock(spec=Session)
    
    mock_tx = MagicMock()
    mock_tx.operation = OperationType.buy
    mock_tx.quantity = 100.0
    
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [mock_tx]
    db.query.return_value = mock_query
    
    qty = _calc_current_quantity(db, portfolio_id=1, ticker="VALE3")
    
    assert qty == 100.0


@pytest.mark.asyncio
async def test_calc_current_quantity_buy_and_sell():
    from app.services.transaction_service import _calc_current_quantity
    
    db = MagicMock(spec=Session)
    
    mock_buy = MagicMock()
    mock_buy.operation = OperationType.buy
    mock_buy.quantity = 200.0
    
    mock_sell = MagicMock()
    mock_sell.operation = OperationType.sell
    mock_sell.quantity = 50.0
    
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [mock_buy, mock_sell]
    db.query.return_value = mock_query
    
    qty = _calc_current_quantity(db, portfolio_id=1, ticker="VALE3")
    
    assert qty == 150.0


@pytest.mark.asyncio
async def test_calc_current_quantity_all_sold():
    from app.services.transaction_service import _calc_current_quantity
    
    db = MagicMock(spec=Session)
    
    mock_buy = MagicMock()
    mock_buy.operation = OperationType.buy
    mock_buy.quantity = 100.0
    
    mock_sell = MagicMock()
    mock_sell.operation = OperationType.sell
    mock_sell.quantity = 100.0
    
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [mock_buy, mock_sell]
    db.query.return_value = mock_query
    
    qty = _calc_current_quantity(db, portfolio_id=1, ticker="VALE3")
    
    assert qty == 0.0


@pytest.mark.asyncio
async def test_calc_current_quantity_oversold():
    from app.services.transaction_service import _calc_current_quantity
    
    db = MagicMock(spec=Session)
    
    mock_buy = MagicMock()
    mock_buy.operation = OperationType.buy
    mock_buy.quantity = 100.0
    
    mock_sell = MagicMock()
    mock_sell.operation = OperationType.sell
    mock_sell.quantity = 150.0
    
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [mock_buy, mock_sell]
    db.query.return_value = mock_query
    
    qty = _calc_current_quantity(db, portfolio_id=1, ticker="VALE3")
    
    assert qty == 0.0
