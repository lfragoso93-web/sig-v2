import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.irpf_service import (
    calc_bens_direitos,
    calc_ganhos_capital,
    calc_rendimentos,
    generate_irpf_pdf,
    generate_irpf_csv,
)
from app.models.transaction import OperationType
from app.models.dividend import DividendStatus


@pytest.mark.asyncio
async def test_calc_bens_direitos_no_transactions():
    db = AsyncMock(spec=AsyncSession)
    
    result = MagicMock()
    result.scalars().all.return_value = []
    db.execute.return_value = result
    
    bens = await calc_bens_direitos(db, portfolio_id=1, year=2024)
    
    assert bens == []


@pytest.mark.asyncio
async def test_calc_bens_direitos_single_position():
    db = AsyncMock(spec=AsyncSession)
    
    mock_tx = MagicMock()
    mock_tx.ticker = "VALE3"
    mock_tx.operation = OperationType.buy
    mock_tx.asset_type = "STOCK"
    mock_tx.quantity = 100.0
    mock_tx.price = 50.0
    mock_tx.date = date(2024, 1, 15)
    mock_tx.currency = "BRL"
    mock_tx.fees = 10.0
    
    result = MagicMock()
    result.scalars().all.return_value = [mock_tx]
    db.execute.return_value = result
    
    bens = await calc_bens_direitos(db, portfolio_id=1, year=2024)
    
    assert len(bens) == 1
    assert bens[0].ticker == "VALE3"
    assert bens[0].quantidade == 100.0


@pytest.mark.asyncio
async def test_calc_bens_direitos_buy_and_sell():
    db = AsyncMock(spec=AsyncSession)
    
    mock_buy = MagicMock()
    mock_buy.ticker = "PETR4"
    mock_buy.operation = OperationType.buy
    mock_buy.asset_type = "STOCK"
    mock_buy.quantity = 200.0
    mock_buy.price = 30.0
    mock_buy.date = date(2024, 1, 15)
    mock_buy.currency = "BRL"
    mock_buy.fees = 20.0
    
    mock_sell = MagicMock()
    mock_sell.ticker = "PETR4"
    mock_sell.operation = OperationType.sell
    mock_sell.asset_type = "STOCK"
    mock_sell.quantity = 50.0
    mock_sell.price = 35.0
    mock_sell.date = date(2024, 6, 15)
    mock_sell.currency = "BRL"
    mock_sell.fees = 0.0
    
    result = MagicMock()
    result.scalars().all.return_value = [mock_buy, mock_sell]
    db.execute.return_value = result
    
    bens = await calc_bens_direitos(db, portfolio_id=1, year=2024)
    
    assert len(bens) == 1
    assert bens[0].ticker == "PETR4"
    assert bens[0].quantidade == 150.0


@pytest.mark.asyncio
async def test_calc_ganhos_capital_no_transactions():
    db = AsyncMock(spec=AsyncSession)
    
    result = MagicMock()
    result.scalars().all.return_value = []
    db.execute.return_value = result
    
    ganhos = await calc_ganhos_capital(db, portfolio_id=1, year=2024)
    
    assert ganhos == {}


@pytest.mark.asyncio
async def test_calc_ganhos_capital_simple_sell():
    db = AsyncMock(spec=AsyncSession)
    
    mock_buy = MagicMock()
    mock_buy.ticker = "VALE3"
    mock_buy.operation = OperationType.buy
    mock_buy.asset_type = "STOCK"
    mock_buy.quantity = 100.0
    mock_buy.price = 50.0
    mock_buy.date = date(2024, 1, 15)
    mock_buy.currency = "BRL"
    mock_buy.fees = 0.0
    
    mock_sell = MagicMock()
    mock_sell.ticker = "VALE3"
    mock_sell.operation = OperationType.sell
    mock_sell.asset_type = "STOCK"
    mock_sell.quantity = 100.0
    mock_sell.price = 60.0
    mock_sell.date = date(2024, 6, 15)
    mock_sell.currency = "BRL"
    mock_sell.fees = 0.0
    
    result = MagicMock()
    result.scalars().all.return_value = [mock_buy, mock_sell]
    db.execute.return_value = result
    
    ganhos = await calc_ganhos_capital(db, portfolio_id=1, year=2024)
    
    assert len(ganhos) > 0


@pytest.mark.asyncio
async def test_calc_rendimentos_no_dividends():
    db = AsyncMock(spec=AsyncSession)
    
    result = MagicMock()
    result.scalars().all.return_value = []
    db.execute.return_value = result
    
    rendimentos = await calc_rendimentos(db, portfolio_id=1, year=2024)
    
    assert rendimentos.isentos == []
    assert rendimentos.jcp == []


@pytest.mark.asyncio
async def test_generate_irpf_pdf_valid():
    from app.schemas.irpf import IRPFReportOut, IRPFResumo
    
    report = IRPFReportOut(
        year=2024,
        portfolio_id=1,
        bens_direitos=[],
        ganhos_capital_mensal={},
        rendimentos=IRPFResumo(isentos=[], jcp=[]),
        resumo={
            "total_bens": 0.0,
            "total_ganhos_realizado": 0.0,
            "total_ganhos_base_calculo": 0.0,
            "aliquesta_media": 0.0,
            "irpf_devido": 0.0,
            "rendimentos_isentos": 0.0,
            "jcp_recebido": 0.0,
        }
    )
    
    pdf_bytes = generate_irpf_pdf(report)
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


@pytest.mark.asyncio
async def test_generate_irpf_csv_valid():
    from app.schemas.irpf import IRPFReportOut, IRPFResumo
    
    report = IRPFReportOut(
        year=2024,
        portfolio_id=1,
        bens_direitos=[],
        ganhos_capital_mensal={},
        rendimentos=IRPFResumo(isentos=[], jcp=[]),
        resumo={
            "total_bens": 0.0,
            "total_ganhos_realizado": 0.0,
            "total_ganhos_base_calculo": 0.0,
            "aliquesta_media": 0.0,
            "irpf_devido": 0.0,
            "rendimentos_isentos": 0.0,
            "jcp_recebido": 0.0,
        }
    )
    
    csv_str = generate_irpf_csv(report)
    
    assert isinstance(csv_str, str)
    assert len(csv_str) > 0
    assert "2024" in csv_str


@pytest.mark.asyncio
async def test_detect_day_trades():
    from app.services.irpf_service import _detect_day_trades
    
    mock_buy = MagicMock()
    mock_buy.date = date(2024, 1, 15)
    mock_buy.ticker = "VALE3"
    mock_buy.operation = OperationType.buy
    
    mock_sell = MagicMock()
    mock_sell.date = date(2024, 1, 15)
    mock_sell.ticker = "VALE3"
    mock_sell.operation = OperationType.sell
    
    day_trades = _detect_day_trades([mock_buy, mock_sell])
    
    assert (date(2024, 1, 15), "VALE3") in day_trades


@pytest.mark.asyncio
async def test_codigo_irpf():
    from app.services.irpf_service import _codigo_irpf
    
    assert _codigo_irpf("ACAO") == ("31", "03 - Participacoes Societarias")
    assert _codigo_irpf("FII") == ("73", "07 - Fundos")
    assert _codigo_irpf("ETF") == ("74", "07 - Fundos")
    assert _codigo_irpf("CRIPTO") == ("08", "08 - Criptoativos")
    assert _codigo_irpf("UNKNOWN")[0] == "99"
