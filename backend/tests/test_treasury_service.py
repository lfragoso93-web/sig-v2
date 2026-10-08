import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.services.treasury_service import (
    list_treasury,
    get_treasury_by_portfolio,
    enrich_with_current_prices,
)
from app.models.transaction import OperationType


@pytest.fixture(autouse=True)
def persisted_treasury_names():
    with patch(
        "app.services.treasury_service.get_persisted_treasury_commercial_names",
        new=AsyncMock(
            return_value={
                "tesouro-ipca-15052029": "Tesouro IPCA+ 15/05/2029",
                "tesouro-selic-01032025": "Tesouro Selic 01/03/2025",
            }
        ),
    ):
        yield


@pytest.mark.asyncio
async def test_list_treasury_unauthorized():
    db = AsyncMock(spec=AsyncSession)

    portfolio_result = MagicMock()
    portfolio_result.scalar_one_or_none.return_value = None
    db.execute.return_value = portfolio_result

    with pytest.raises(HTTPException) as exc_info:
        await list_treasury(db, portfolio_id=1, user_id=999)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_list_treasury_no_transactions():
    db = AsyncMock(spec=AsyncSession)

    portfolio_result = MagicMock()
    portfolio_result.scalar_one_or_none.return_value = MagicMock()

    tx_result = MagicMock()
    tx_result.scalars().all.return_value = []

    db.execute.side_effect = [portfolio_result, tx_result]

    result = await list_treasury(db, portfolio_id=1, user_id=1)

    assert result == []


@pytest.mark.asyncio
async def test_list_treasury_with_treasury():
    db = AsyncMock(spec=AsyncSession)

    portfolio_result = MagicMock()
    portfolio_result.scalar_one_or_none.return_value = MagicMock()

    mock_tx = MagicMock()
    mock_tx.id = 1
    mock_tx.portfolio_id = 1
    mock_tx.ticker = "Tesouro IPCA+ 2029"
    mock_tx.asset_type = "tesouro_direto"
    mock_tx.operation = OperationType.buy
    mock_tx.price = 3000.0
    mock_tx.quantity = 1.0
    mock_tx.date = date(2024, 1, 15)
    mock_tx.notes = None

    tx_result = MagicMock()
    tx_result.scalars().all.return_value = [mock_tx]

    db.execute.side_effect = [portfolio_result, tx_result]

    with patch(
        "app.services.treasury_service.resolve_treasury_symbol",
        new=AsyncMock(return_value="tesouro-ipca-15052029"),
    ), patch(
        "app.services.treasury_service.get_persisted_current_prices",
        new=AsyncMock(return_value={"TESOURO-IPCA-15052029": 3100.0}),
    ):
        result = await list_treasury(db, portfolio_id=1, user_id=1)

    assert len(result) == 1
    assert result[0]["ticker"] == "Tesouro IPCA+ 2029"
    assert result[0]["commercial_name"] == "Tesouro IPCA+ 15/05/2029"
    assert result[0]["valor_atual"] == 3100.0


@pytest.mark.asyncio
async def test_list_treasury_filters_non_treasury():
    db = AsyncMock(spec=AsyncSession)

    portfolio_result = MagicMock()
    portfolio_result.scalar_one_or_none.return_value = MagicMock()

    mock_treasury = MagicMock()
    mock_treasury.id = 1
    mock_treasury.portfolio_id = 1
    mock_treasury.ticker = "Tesouro IPCA+ 2029"
    mock_treasury.asset_type = "tesouro_direto"
    mock_treasury.operation = OperationType.buy
    mock_treasury.price = 3000.0
    mock_treasury.quantity = 1.0
    mock_treasury.date = date(2024, 1, 15)
    mock_treasury.notes = None

    mock_stock = MagicMock()
    mock_stock.id = 2
    mock_stock.portfolio_id = 1
    mock_stock.ticker = "VALE3"
    mock_stock.asset_type = "STOCK"
    mock_stock.operation = OperationType.buy

    tx_result = MagicMock()
    tx_result.scalars().all.return_value = [mock_treasury, mock_stock]

    db.execute.side_effect = [portfolio_result, tx_result]

    with patch(
        "app.services.treasury_service.resolve_treasury_symbol",
        new=AsyncMock(return_value="tesouro-ipca-15052029"),
    ), patch(
        "app.services.treasury_service.get_persisted_current_prices",
        new=AsyncMock(return_value={"TESOURO-IPCA-15052029": 3100.0}),
    ):
        result = await list_treasury(db, portfolio_id=1, user_id=1)

    assert len(result) == 1
    assert result[0]["ticker"] == "Tesouro IPCA+ 2029"


@pytest.mark.asyncio
async def test_get_treasury_by_portfolio_no_auth():
    db = AsyncMock(spec=AsyncSession)

    tx_result = MagicMock()
    tx_result.scalars().all.return_value = []
    db.execute.return_value = tx_result

    result = await get_treasury_by_portfolio(db, portfolio_id=1)

    assert result == []


@pytest.mark.asyncio
async def test_get_treasury_by_portfolio_with_data():
    db = AsyncMock(spec=AsyncSession)

    mock_tx = MagicMock()
    mock_tx.ticker = "Tesouro IPCA+ 2029"
    mock_tx.asset_type = "tesouro_direto"

    tx_result = MagicMock()
    tx_result.scalars().all.return_value = [mock_tx]
    db.execute.return_value = tx_result

    result = await get_treasury_by_portfolio(db, portfolio_id=1)

    assert len(result) == 1


@pytest.mark.asyncio
async def test_enrich_with_current_prices_empty():
    result = await enrich_with_current_prices(AsyncMock(spec=AsyncSession), [])

    assert result == []


@pytest.mark.asyncio
async def test_enrich_with_current_prices_single():
    db = AsyncMock(spec=AsyncSession)
    mock_tx = MagicMock()
    mock_tx.id = 1
    mock_tx.portfolio_id = 1
    mock_tx.ticker = "Tesouro IPCA+ 2029"
    mock_tx.price = 3000.0
    mock_tx.quantity = 1.0
    mock_tx.date = date(2024, 1, 15)
    mock_tx.notes = "Test note"

    with patch(
        "app.services.treasury_service.resolve_treasury_symbol",
        new=AsyncMock(return_value="tesouro-ipca-15052029"),
    ), patch(
        "app.services.treasury_service.get_persisted_current_prices",
        new=AsyncMock(return_value={"TESOURO-IPCA-15052029": 3100.0}),
    ):
        result = await enrich_with_current_prices(db, [mock_tx])

    assert len(result) == 1
    assert result[0]["valor_atual"] == 3100.0
    assert result[0]["lucro_prejuizo"] == 100.0
    assert result[0]["rentabilidade_pct"] == pytest.approx(3.3333, rel=1e-3)
    assert result[0]["commercial_name"] == "Tesouro IPCA+ 15/05/2029"


@pytest.mark.asyncio
async def test_enrich_with_current_prices_no_price():
    db = AsyncMock(spec=AsyncSession)
    mock_tx = MagicMock()
    mock_tx.id = 1
    mock_tx.portfolio_id = 1
    mock_tx.ticker = "Tesouro IPCA+ 2029"
    mock_tx.price = 3000.0
    mock_tx.quantity = 1.0
    mock_tx.date = date(2024, 1, 15)
    mock_tx.notes = None

    with patch(
        "app.services.treasury_service.resolve_treasury_symbol",
        new=AsyncMock(return_value="tesouro-ipca-15052029"),
    ), patch(
        "app.services.treasury_service.get_persisted_current_prices",
        new=AsyncMock(return_value={}),
    ):
        result = await enrich_with_current_prices(db, [mock_tx])

    assert len(result) == 1
    assert result[0]["current_price"] is None
    assert result[0]["valor_atual"] is None
    assert result[0]["lucro_prejuizo"] is None


@pytest.mark.asyncio
async def test_enrich_with_current_prices_multiple():
    db = AsyncMock(spec=AsyncSession)
    mock_tx1 = MagicMock()
    mock_tx1.id = 1
    mock_tx1.portfolio_id = 1
    mock_tx1.ticker = "Tesouro IPCA+ 2029"
    mock_tx1.price = 3000.0
    mock_tx1.quantity = 1.0
    mock_tx1.date = date(2024, 1, 15)
    mock_tx1.notes = None

    mock_tx2 = MagicMock()
    mock_tx2.id = 2
    mock_tx2.portfolio_id = 1
    mock_tx2.ticker = "Tesouro SELIC 2025"
    mock_tx2.price = 1000.0
    mock_tx2.quantity = 2.0
    mock_tx2.date = date(2024, 2, 15)
    mock_tx2.notes = None

    async def resolve_symbol(_db, ticker):
        return {
            "Tesouro IPCA+ 2029": "tesouro-ipca-15052029",
            "Tesouro SELIC 2025": "tesouro-selic-01032025",
        }[ticker]

    with patch(
        "app.services.treasury_service.resolve_treasury_symbol",
        side_effect=resolve_symbol,
    ), patch(
        "app.services.treasury_service.get_persisted_current_prices",
        new=AsyncMock(
            return_value={
                "TESOURO-IPCA-15052029": 3100.0,
                "TESOURO-SELIC-01032025": 1050.0,
            }
        ),
    ):
        result = await enrich_with_current_prices(db, [mock_tx1, mock_tx2])

    assert len(result) == 2
    assert result[0]["valor_atual"] == 3100.0
    assert result[1]["valor_atual"] == 2100.0


@pytest.mark.asyncio
async def test_enrich_with_current_prices_fails_closed_on_catalog_error():
    db = AsyncMock(spec=AsyncSession)
    mock_tx = MagicMock(ticker="Tesouro IPCA+ 2029")

    with patch(
        "app.services.treasury_service.resolve_treasury_symbol",
        new=AsyncMock(side_effect=RuntimeError("catalog unavailable")),
    ), pytest.raises(RuntimeError, match="catalog unavailable"):
        await enrich_with_current_prices(db, [mock_tx])


@pytest.mark.asyncio
async def test_is_treasury():
    from app.services.treasury_service import _is_treasury

    assert _is_treasury("tesouro_direto") is True
    assert _is_treasury("tesouro direto") is True
    assert _is_treasury("treasury") is True
    assert _is_treasury("TESOURO_DIRETO") is True
    assert _is_treasury("STOCK") is False
    assert _is_treasury(None) is False
    assert _is_treasury("") is False
