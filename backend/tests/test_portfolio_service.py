from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.transaction import OperationType
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.services.portfolio_service import (
    build_asset_distribution_items,
    build_group_performance_metrics,
    calc_raw_positions,
    create_portfolio,
    delete_portfolio,
    get_portfolio,
    get_portfolio_positions,
    get_portfolio_summary,
    list_portfolios,
    sum_dividends,
    update_portfolio,
)
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_list_portfolios_empty():
    db = AsyncMock(spec=AsyncSession)
    
    result = MagicMock()
    result.scalars().all.return_value = []
    db.execute.return_value = result
    
    portfolios = await list_portfolios(db, user_id=1)
    
    assert portfolios == []


@pytest.mark.asyncio
async def test_list_portfolios_with_data():
    db = AsyncMock(spec=AsyncSession)
    
    mock_portfolio = MagicMock()
    mock_portfolio.id = 1
    mock_portfolio.name = "Meu Portfolio"
    mock_portfolio.user_id = 1
    
    result = MagicMock()
    result.scalars().all.return_value = [mock_portfolio]
    db.execute.return_value = result
    
    portfolios = await list_portfolios(db, user_id=1)
    
    assert len(portfolios) == 1
    assert portfolios[0].id == 1


@pytest.mark.asyncio
async def test_create_portfolio():
    db = AsyncMock(spec=AsyncSession)
    
    data = PortfolioCreate(name="Nova Carteira")
    
    with patch('app.services.portfolio_service.Portfolio') as mock_portfolio_cls:
        mock_portfolio = MagicMock()
        mock_portfolio.id = 1
        mock_portfolio.name = "Nova Carteira"
        mock_portfolio_cls.return_value = mock_portfolio
        
        db.add = MagicMock()
        db.flush = AsyncMock()
        
        result = await create_portfolio(db, user_id=1, data=data)
        
        assert result.name == "Nova Carteira"


@pytest.mark.asyncio
async def test_get_portfolio_not_found():
    db = AsyncMock(spec=AsyncSession)
    
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    
    with pytest.raises(HTTPException) as exc_info:
        await get_portfolio(db, portfolio_id=999, user_id=1)
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_portfolio_success():
    db = AsyncMock(spec=AsyncSession)
    
    mock_portfolio = MagicMock()
    mock_portfolio.id = 1
    mock_portfolio.name = "Meu Portfolio"
    mock_portfolio.user_id = 1
    
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_portfolio
    db.execute.return_value = result
    
    portfolio = await get_portfolio(db, portfolio_id=1, user_id=1)
    
    assert portfolio.id == 1
    assert portfolio.name == "Meu Portfolio"


@pytest.mark.asyncio
async def test_update_portfolio_not_found():
    db = AsyncMock(spec=AsyncSession)
    
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    
    data = PortfolioUpdate(name="Updated")
    
    with pytest.raises(HTTPException) as exc_info:
        await update_portfolio(db, portfolio_id=999, user_id=1, data=data)
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_portfolio_success():
    db = AsyncMock(spec=AsyncSession)
    
    mock_portfolio = MagicMock()
    mock_portfolio.id = 1
    mock_portfolio.name = "Meu Portfolio"
    mock_portfolio.user_id = 1
    
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_portfolio
    db.execute.return_value = result
    
    db.flush = AsyncMock()
    
    data = PortfolioUpdate(name="Portfolio Atualizado")
    portfolio = await update_portfolio(db, portfolio_id=1, user_id=1, data=data)
    
    assert portfolio.name == "Portfolio Atualizado"


@pytest.mark.asyncio
async def test_delete_portfolio_not_found():
    db = AsyncMock(spec=AsyncSession)
    
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    
    with pytest.raises(HTTPException) as exc_info:
        await delete_portfolio(db, portfolio_id=999, user_id=1)
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_portfolio_success():
    db = AsyncMock(spec=AsyncSession)
    
    mock_portfolio = MagicMock()
    mock_portfolio.id = 1
    mock_portfolio.user_id = 1
    
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_portfolio
    db.execute.return_value = result
    
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    
    await delete_portfolio(db, portfolio_id=1, user_id=1)
    
    db.delete.assert_called()


@pytest.mark.asyncio
async def test_calc_raw_positions_no_transactions():
    db = AsyncMock(spec=AsyncSession)
    
    result = MagicMock()
    result.scalars().all.return_value = []
    db.execute.return_value = result
    
    positions = await calc_raw_positions(db, portfolio_id=1)
    
    assert positions == []


@pytest.mark.asyncio
async def test_calc_raw_positions_single_buy():
    db = AsyncMock(spec=AsyncSession)
    
    mock_tx = MagicMock()
    mock_tx.ticker = "VALE3"
    mock_tx.operation = OperationType.buy
    mock_tx.asset_type = "ACAO"
    mock_tx.quantity = 100.0
    mock_tx.price = 50.0
    mock_tx.fees = 10.0
    mock_tx.date = date(2024, 1, 15)
    mock_tx.currency = "BRL"
    mock_tx.fx_rate = None
    
    result = MagicMock()
    result.scalars().all.return_value = [mock_tx]
    db.execute.return_value = result
    
    positions = await calc_raw_positions(db, portfolio_id=1)
    
    assert len(positions) == 1
    assert positions[0]["ticker"] == "VALE3"
    assert positions[0]["quantity"] == 100.0


@pytest.mark.asyncio
async def test_calc_raw_positions_buy_and_sell():
    db = AsyncMock(spec=AsyncSession)
    
    mock_buy = MagicMock()
    mock_buy.ticker = "PETR4"
    mock_buy.operation = OperationType.buy
    mock_buy.asset_type = "ACAO"
    mock_buy.quantity = 200.0
    mock_buy.price = 30.0
    mock_buy.fees = 20.0
    mock_buy.date = date(2024, 1, 15)
    mock_buy.currency = "BRL"
    mock_buy.fx_rate = None
    
    mock_sell = MagicMock()
    mock_sell.ticker = "PETR4"
    mock_sell.operation = OperationType.sell
    mock_sell.asset_type = "ACAO"
    mock_sell.quantity = 50.0
    mock_sell.price = 35.0
    mock_sell.fees = 0.0
    mock_sell.date = date(2024, 6, 15)
    mock_sell.currency = "BRL"
    mock_sell.fx_rate = None
    
    result = MagicMock()
    result.scalars().all.return_value = [mock_buy, mock_sell]
    db.execute.return_value = result
    
    positions = await calc_raw_positions(db, portfolio_id=1)
    
    assert len(positions) == 1
    assert positions[0]["ticker"] == "PETR4"
    assert positions[0]["quantity"] == 150.0


@pytest.mark.asyncio
async def test_sum_dividends_zero():
    db = AsyncMock(spec=AsyncSession)

    with patch(
        "app.services.portfolio_service.load_portfolio_dividend_entitlements",
        new=AsyncMock(return_value=[]),
    ):
        total = await sum_dividends(db, portfolio_id=1)
    
    assert total == 0.0


@pytest.mark.asyncio
async def test_sum_dividends_with_cutoff():
    db = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "app.services.portfolio_service.load_portfolio_dividend_entitlements",
            new=AsyncMock(return_value=[object()]),
        ),
        patch(
            "app.services.portfolio_service.aggregate_received_entitlements",
            return_value=1500.0,
        ),
    ):
        total = await sum_dividends(db, portfolio_id=1, cutoff=date(2024, 1, 1))
    
    assert total == 1500.0


@pytest.mark.asyncio
async def test_get_portfolio_summary_not_found():
    db = AsyncMock(spec=AsyncSession)
    
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    
    with pytest.raises(HTTPException) as exc_info:
        await get_portfolio_summary(db, portfolio_id=999, user_id=1)
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_portfolio_positions_not_found():
    db = AsyncMock(spec=AsyncSession)
    
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    
    with pytest.raises(HTTPException) as exc_info:
        await get_portfolio_positions(db, portfolio_id=999, user_id=1)
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_normalize_type():
    from app.services.portfolio_service import normalize_type
    
    assert normalize_type("ACAO") == "ACAO"
    assert normalize_type("acao") == "ACAO"
    assert normalize_type("ACAO_NACIONAL") == "ACAO"
    assert normalize_type("ETF_INT") == "ETF_INTERNACIONAL"
    assert normalize_type("TESOURO") == "TESOURO_DIRETO"
    assert normalize_type(None) == ""


@pytest.mark.asyncio
async def test_is_buy():
    from app.services.portfolio_service import _is_buy
    
    assert _is_buy(OperationType.buy) is True
    assert _is_buy("buy") is True
    assert _is_buy("compra") is True
    assert _is_buy(OperationType.sell) is False
    assert _is_buy("sell") is False


@pytest.mark.asyncio
async def test_is_sell():
    from app.services.portfolio_service import _is_sell
    
    assert _is_sell(OperationType.sell) is True
    assert _is_sell("sell") is True
    assert _is_sell("venda") is True
    assert _is_sell(OperationType.buy) is False
    assert _is_sell("buy") is False


def test_group_metrics_positive_rentabilidade_negative_variation():
    metrics = build_group_performance_metrics(
        current_value=1100.0,
        total_invested=1000.0,
        previous_value=1200.0,
    )

    assert metrics["rentabilidade_pct"] == 10.0
    assert metrics["daily_variation_pct"] == pytest.approx(-8.3333, rel=1e-4)


def test_group_metrics_negative_rentabilidade_positive_variation():
    metrics = build_group_performance_metrics(
        current_value=900.0,
        total_invested=1000.0,
        previous_value=800.0,
    )

    assert metrics["rentabilidade_pct"] == -10.0
    assert metrics["daily_variation_pct"] == 12.5


def test_group_metrics_without_historical_reference():
    metrics = build_group_performance_metrics(
        current_value=1100.0,
        total_invested=1000.0,
        previous_value=None,
    )

    assert metrics["rentabilidade_pct"] == 10.0
    assert metrics["daily_variation_value"] is None
    assert metrics["daily_variation_pct"] is None


def test_asset_distribution_ignores_empty_classes():
    items = build_asset_distribution_items({
        "ACAO": 100.0,
        "FII": 300.0,
        "CRIPTO": 0.0,
    })

    assert [item["asset_type"] for item in items] == ["FII", "ACAO"]
    assert sum(item["percentage"] for item in items) == pytest.approx(100.0)


def test_asset_distribution_supported_classes_sum_to_100():
    items = build_asset_distribution_items({
        "RENDA_FIXA": 250.0,
        "TESOURO_DIRETO": 250.0,
        "STOCK": 250.0,
        "CRIPTO": 250.0,
    })

    assert {item["asset_type"] for item in items} == {
        "RENDA_FIXA",
        "TESOURO_DIRETO",
        "STOCK",
        "CRIPTO",
    }
    assert sum(item["value"] for item in items) == 1000.0
    assert sum(item["percentage"] for item in items) == pytest.approx(100.0)
