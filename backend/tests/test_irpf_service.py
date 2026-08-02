from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType
from app.services.canonical_dividend_entitlement import (
    DividendEntitlement,
    DividendEvent,
    EntitlementReason,
)
from app.services.canonical_dividend_entitlement_reader import (
    PortfolioDividendEntitlement,
)
from app.services.irpf_service import (
    calc_ganhos_capital,
    calc_rendimentos,
    generate_irpf_csv,
    generate_irpf_pdf,
)


@pytest.mark.asyncio
async def test_calc_ganhos_capital_no_transactions():
    db = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalars().all.return_value = []
    db.execute.return_value = result

    ganhos = await calc_ganhos_capital(db, portfolio_id=1, year=2024)

    assert ganhos == []


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
    with patch(
        "app.services.irpf_service.load_portfolio_dividend_entitlements",
        new=AsyncMock(return_value=[]),
    ):
        dividendos, jcp = await calc_rendimentos(db, portfolio_id=1, year=2024)

    assert (dividendos, jcp) == ([], [])


def _entitlement(
    *,
    event_id: int,
    ticker: str,
    event_type: str,
    payment_date: date | None,
    gross: str,
    tax: str = "0",
    currency: str = "BRL",
    reason: EntitlementReason = EntitlementReason.ELIGIBLE,
) -> PortfolioDividendEntitlement:
    gross_amount = Decimal(gross)
    withholding_tax = Decimal(tax)
    event = DividendEvent(
        event_id=event_id,
        record_date=date(2024, 4, 1),
        ex_date=date(2024, 4, 2),
        payment_date=payment_date,
        event_type=event_type,
        value_per_unit=Decimal("1"),
        currency=currency,
    )
    right = DividendEntitlement(
        event_id=event_id,
        reason=reason,
        entitlement_date=event.record_date,
        eligible_quantity=Decimal("100"),
        gross_amount=gross_amount,
        withholding_tax=withholding_tax,
        net_amount=gross_amount - withholding_tax,
        currency=currency,
    )
    return PortfolioDividendEntitlement(
        ticker=ticker,
        asset_type="ACAO",
        event=event,
        entitlement=right,
        approved_on=None,
        gross_value_per_unit=None,
        factor=None,
        complete_factor=None,
        isin_code=None,
        asset_issued=None,
        related_to=None,
        remarks=None,
    )


@pytest.mark.asyncio
async def test_calc_rendimentos_uses_canonical_net_values():
    db = AsyncMock(spec=AsyncSession)
    rights = [
        _entitlement(
            event_id=1,
            ticker="VALE3",
            event_type="DIVIDENDO",
            payment_date=date(2024, 5, 10),
            gross="100",
        ),
        _entitlement(
            event_id=2,
            ticker="PETR4",
            event_type="JCP",
            payment_date=date(2024, 6, 10),
            gross="200",
            tax="30",
        ),
    ]
    with patch(
        "app.services.irpf_service.load_portfolio_dividend_entitlements",
        new=AsyncMock(return_value=rights),
    ):
        dividendos, jcp = await calc_rendimentos(db, 1, 2024)

    assert dividendos[0].ticker == "VALE3"
    assert dividendos[0].total_recebido == 100
    assert dividendos[0].asset_type == "ACAO"
    assert jcp[0].total_bruto == 200
    assert jcp[0].ir_retido == 30
    assert jcp[0].total_liquido == 170


@pytest.mark.asyncio
async def test_calc_rendimentos_excludes_non_brl_and_unpaid_rights():
    db = AsyncMock(spec=AsyncSession)
    rights = [
        _entitlement(
            event_id=1,
            ticker="AAPL",
            event_type="DIVIDENDO",
            payment_date=date(2024, 5, 10),
            gross="100",
            currency="USD",
        ),
        _entitlement(
            event_id=2,
            ticker="VALE3",
            event_type="DIVIDENDO",
            payment_date=None,
            gross="100",
        ),
    ]
    with patch(
        "app.services.irpf_service.load_portfolio_dividend_entitlements",
        new=AsyncMock(return_value=rights),
    ):
        dividendos, jcp = await calc_rendimentos(db, 1, 2024)

    assert (dividendos, jcp) == ([], [])


@pytest.mark.asyncio
async def test_generate_irpf_pdf_valid():
    from app.schemas.irpf import IRPFReportOut, IRPFResumo

    report = IRPFReportOut(
        portfolio_id=1,
        ano=2024,
        bens_direitos=[],
        ganhos_mensais=[],
        dividendos=[],
        jcp=[],
        resumo=IRPFResumo(
            ano=2024,
            total_bens_direitos=0.0,
            total_vendas_ano=0.0,
            lucro_tributavel_swing=0.0,
            lucro_tributavel_day_trade=0.0,
            ir_swing_trade_devido=0.0,
            ir_day_trade_devido=0.0,
            ir_retido_fonte_total=0.0,
            ir_a_recolher_total=0.0,
            total_dividendos_isentos=0.0,
            total_jcp_bruto=0.0,
            total_jcp_ir_retido=0.0,
            prejuizo_acumulado=0.0,
        ),
    )

    pdf_bytes = generate_irpf_pdf(report)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


@pytest.mark.asyncio
async def test_generate_irpf_csv_valid():
    from app.schemas.irpf import IRPFReportOut, IRPFResumo

    report = IRPFReportOut(
        portfolio_id=1,
        ano=2024,
        bens_direitos=[],
        ganhos_mensais=[],
        dividendos=[],
        jcp=[],
        resumo=IRPFResumo(
            ano=2024,
            total_bens_direitos=0.0,
            total_vendas_ano=0.0,
            lucro_tributavel_swing=0.0,
            lucro_tributavel_day_trade=0.0,
            ir_swing_trade_devido=0.0,
            ir_day_trade_devido=0.0,
            ir_retido_fonte_total=0.0,
            ir_a_recolher_total=0.0,
            total_dividendos_isentos=0.0,
            total_jcp_bruto=0.0,
            total_jcp_ir_retido=0.0,
            prejuizo_acumulado=0.0,
        ),
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
