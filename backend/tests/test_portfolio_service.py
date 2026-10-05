from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.transaction import OperationType
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate
from app.services import portfolio_service
from app.services.benchmark_rate_service import BenchmarkCoverageStatus
from app.services.fixed_income_valuation_service import (
    FixedIncomeKey,
    FixedIncomeValuation,
    IncompleteBenchmarkCoverageError,
)
from app.services.portfolio_service import (
    build_group_performance_metrics,
    calc_raw_positions,
    create_portfolio,
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
async def test_get_portfolio_positions_degrades_when_fixed_income_benchmark_is_partial(monkeypatch):
    db = AsyncMock(spec=AsyncSession)
    enriched_positions = [
        {
            "ticker": "PETR4",
            "asset_type": "ACAO",
            "quantity": 100.0,
            "avg_price": 10.0,
            "avg_price_usd": None,
            "total_invested": 1_000.0,
            "current_price": 12.0,
            "current_price_usd": None,
            "current_value": 1_200.0,
            "result_abs": 200.0,
            "result_pct": 20.0,
            "is_usd": False,
        },
    ]

    monkeypatch.setattr(portfolio_service, "cache_get", AsyncMock(return_value=None))
    monkeypatch.setattr(portfolio_service, "cache_set", AsyncMock())
    monkeypatch.setattr(portfolio_service, "get_portfolio", AsyncMock(return_value=object()))
    monkeypatch.setattr(
        portfolio_service,
        "_non_fixed_income_enriched",
        AsyncMock(return_value=enriched_positions),
    )
    monkeypatch.setattr(portfolio_service, "get_targets_map", AsyncMock(return_value={}))
    monkeypatch.setattr(
        portfolio_service,
        "_fetch_previous_prices_batch",
        AsyncMock(return_value=({}, None)),
    )
    monkeypatch.setattr(portfolio_service, "_fetch_logos_batch", AsyncMock(return_value={}))
    monkeypatch.setattr(portfolio_service, "sum_dividends_by_ticker", AsyncMock(return_value={}))
    monkeypatch.setattr(
        portfolio_service,
        "get_fixed_income_valuations_with_coverage_fallback",
        AsyncMock(
            side_effect=IncompleteBenchmarkCoverageError(
                "CDI",
                date(2026, 4, 14),
                date(2026, 9, 8),
                BenchmarkCoverageStatus.PARTIAL,
            )
        ),
    )
    monkeypatch.setattr(
        portfolio_service,
        "get_fixed_income_principal_valuations",
        AsyncMock(
            return_value=[
                FixedIncomeValuation(
                    key=FixedIncomeKey(
                        name="CDB TESTE",
                        indexer="CDI",
                        rate_pct=Decimal("110.0000"),
                        maturity=None,
                    ),
                    invested_amount=Decimal("3000.00"),
                    current_value=Decimal("3000.00"),
                    income_amount=Decimal("0.00"),
                    income_pct=Decimal("0.0000"),
                    applications_count=1,
                )
            ]
        ),
    )

    positions = await get_portfolio_positions(db, portfolio_id=15, user_id=16)

    assert len(positions) == 2
    assert positions[0]["asset_type"] == "ACAO"
    assert positions[0]["total_value"] == 1_200.0
    assert positions[0]["positions"][0]["ticker"] == "PETR4"
    assert positions[1]["asset_type"] == "RENDA_FIXA"
    assert positions[1]["total_value"] == 3_000.0
    assert positions[1]["positions"][0]["ticker"] == "CDB TESTE"


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

