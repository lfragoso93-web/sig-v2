"""Testes para position_service — calculo de posicoes em carteira."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.position_service import get_positions
from app.models.transaction import Transaction, OperationType


@pytest.mark.asyncio
class TestGetPositions:

    async def test_get_positions_empty_portfolio(self):
        db = AsyncMock(spec=AsyncSession)
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=[])
        
        db.execute = AsyncMock(return_value=execute_result)

        positions = await get_positions(db, portfolio_id=1)

        assert positions == []

    async def test_get_positions_single_buy_transaction(self):
        db = AsyncMock(spec=AsyncSession)
        
        tx = MagicMock(spec=Transaction)
        tx.ticker = "PETR4"
        tx.asset_type = "ACAO"
        tx.quantity = 100.0
        tx.price = 25.50
        tx.fees = 10.0
        tx.operation = OperationType.buy
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=[tx])
        
        db.execute = AsyncMock(return_value=execute_result)

        with AsyncMock() as mock_get_price:
            from unittest.mock import patch
            with patch('app.services.position_service.get_current_price', new_callable=AsyncMock, return_value=30.0):
                positions = await get_positions(db, portfolio_id=1)

        assert len(positions) == 1
        assert positions[0]["ticker"] == "PETR4"
        assert positions[0]["quantity"] == 100.0
        assert positions[0]["asset_type"] == "ACAO"

    async def test_get_positions_buy_and_sell(self):
        db = AsyncMock(spec=AsyncSession)
        
        tx_buy = MagicMock(spec=Transaction)
        tx_buy.ticker = "VALE3"
        tx_buy.asset_type = "ACAO"
        tx_buy.quantity = 50.0
        tx_buy.price = 80.0
        tx_buy.fees = 5.0
        tx_buy.operation = OperationType.buy
        
        tx_sell = MagicMock(spec=Transaction)
        tx_sell.ticker = "VALE3"
        tx_sell.asset_type = "ACAO"
        tx_sell.quantity = 20.0
        tx_sell.price = 85.0
        tx_sell.fees = 0.0
        tx_sell.operation = OperationType.sell
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=[tx_buy, tx_sell])
        
        db.execute = AsyncMock(return_value=execute_result)

        from unittest.mock import patch
        with patch('app.services.position_service.get_current_price', new_callable=AsyncMock, return_value=82.0):
            positions = await get_positions(db, portfolio_id=1)

        assert len(positions) == 1
        assert positions[0]["ticker"] == "VALE3"
        assert positions[0]["quantity"] == 30.0

    async def test_get_positions_complete_sell_removed(self):
        db = AsyncMock(spec=AsyncSession)
        
        tx_buy = MagicMock(spec=Transaction)
        tx_buy.ticker = "IBOV11"
        tx_buy.asset_type = "ETF"
        tx_buy.quantity = 10.0
        tx_buy.price = 100.0
        tx_buy.fees = 0.0
        tx_buy.operation = OperationType.buy
        
        tx_sell = MagicMock(spec=Transaction)
        tx_sell.ticker = "IBOV11"
        tx_sell.asset_type = "ETF"
        tx_sell.quantity = 10.0
        tx_sell.price = 105.0
        tx_sell.fees = 0.0
        tx_sell.operation = OperationType.sell
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=[tx_buy, tx_sell])
        
        db.execute = AsyncMock(return_value=execute_result)

        from unittest.mock import patch
        with patch('app.services.position_service.get_current_price', new_callable=AsyncMock, return_value=106.0):
            positions = await get_positions(db, portfolio_id=1)

        assert positions == []

    async def test_get_positions_multiple_assets(self):
        db = AsyncMock(spec=AsyncSession)
        
        tx1 = MagicMock(spec=Transaction)
        tx1.ticker = "PETR4"
        tx1.asset_type = "ACAO"
        tx1.quantity = 100.0
        tx1.price = 25.0
        tx1.fees = 10.0
        tx1.operation = OperationType.buy
        
        tx2 = MagicMock(spec=Transaction)
        tx2.ticker = "VALE3"
        tx2.asset_type = "ACAO"
        tx2.quantity = 50.0
        tx2.price = 80.0
        tx2.fees = 5.0
        tx2.operation = OperationType.buy
        
        execute_result = AsyncMock()
        execute_result.scalars = AsyncMock(return_value=execute_result)
        execute_result.all = AsyncMock(return_value=[tx1, tx2])
        
        db.execute = AsyncMock(return_value=execute_result)

        from unittest.mock import patch
        with patch('app.services.position_service.get_current_price', new_callable=AsyncMock, return_value=50.0):
            positions = await get_positions(db, portfolio_id=1)

        assert len(positions) == 2
