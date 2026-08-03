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


def _transaction(
    *,
    ticker: str = "VALE3",
    operation: OperationType,
    quantity: float,
    price: float,
    tx_date: date,
    asset_type: str = "STOCK",
    fees: float = 0.0,
) -> MagicMock:
    tx = MagicMock()
    tx.ticker = ticker
    tx.operation = operation
    tx.asset_type = asset_type
    tx.quantity = quantity
    tx.price = price
    tx.date = tx_date
    tx.currency = "BRL"
    tx.fees = fees
    return tx


def _db_with_transactions(
    *,
    current_year: list[MagicMock],
    previous_years: list[MagicMock] | None = None,
) -> AsyncMock:
    current_result = MagicMock()
    current_result.scalars().all.return_value = current_year
    previous_result = MagicMock()
    previous_result.scalars().all.return_value = previous_years or []

    db = AsyncMock(spec=AsyncSession)
    db.execute.side_effect = [current_result, previous_result]
    return db


@pytest.mark.asyncio
async def test_calc_ganhos_capital_no_transactions():
    db = _db_with_transactions(current_year=[])

    ganhos = await calc_ganhos_capital(db, portfolio_id=1, year=2024)

    assert ganhos == []


@pytest.mark.asyncio
async def test_calc_ganhos_capital_simple_stock_sale_preserves_current_exemption():
    db = _db_with_transactions(
        current_year=[
            _transaction(
                operation=OperationType.buy,
                quantity=100,
                price=50,
                tx_date=date(2024, 1, 15),
            ),
            _transaction(
                operation=OperationType.sell,
                quantity=100,
                price=60,
                tx_date=date(2024, 6, 15),
            ),
        ]
    )

    ganhos = await calc_ganhos_capital(db, portfolio_id=1, year=2024)

    assert len(ganhos) == 1
    month = ganhos[0]
    assert month.mes == "2024-06"
    assert month.total_vendas == 6_000
    assert month.total_custo == 5_000
    assert month.lucro_bruto == 1_000
    assert month.isencao_aplicada == 6_000
    assert month.base_calculo == 0
    assert month.ir_a_recolher == 0
    assert month.vendas[0].is_isento is True


@pytest.mark.asyncio
async def test_calc_ganhos_capital_partial_sale_keeps_weighted_average_cost():
    db = _db_with_transactions(
        current_year=[
            _transaction(
                operation=OperationType.sell,
                quantity=40,
                price=15,
                fees=20,
                tx_date=date(2024, 2, 10),
                asset_type="ETF",
            ),
            _transaction(
                operation=OperationType.sell,
                quantity=60,
                price=20,
                tx_date=date(2024, 3, 10),
                asset_type="ETF",
            ),
        ],
        previous_years=[
            _transaction(
                operation=OperationType.buy,
                quantity=100,
                price=10,
                fees=100,
                tx_date=date(2023, 12, 1),
                asset_type="ETF",
            )
        ],
    )

    ganhos = await calc_ganhos_capital(db, portfolio_id=1, year=2024)

    assert [month.mes for month in ganhos] == ["2024-02", "2024-03"]
    assert ganhos[0].total_custo == 440
    assert ganhos[0].lucro_bruto == 140
    assert ganhos[0].ir_devido_swing == 21
    assert ganhos[1].total_custo == 660
    assert ganhos[1].lucro_bruto == 540
    assert ganhos[1].ir_devido_swing == 81


@pytest.mark.asyncio
async def test_calc_ganhos_capital_multiple_buys_use_weighted_average():
    db = _db_with_transactions(
        current_year=[
            _transaction(
                operation=OperationType.buy,
                quantity=10,
                price=10,
                tx_date=date(2024, 1, 2),
                asset_type="ETF",
            ),
            _transaction(
                operation=OperationType.buy,
                quantity=30,
                price=20,
                tx_date=date(2024, 1, 3),
                asset_type="ETF",
            ),
            _transaction(
                operation=OperationType.sell,
                quantity=20,
                price=25,
                tx_date=date(2024, 4, 1),
                asset_type="ETF",
            ),
        ]
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert month.vendas[0].custo_aquisicao == 17.5
    assert month.total_custo == 350
    assert month.lucro_bruto == 150


@pytest.mark.asyncio
async def test_calc_ganhos_capital_zero_position_then_repurchase_resets_cost():
    db = _db_with_transactions(
        current_year=[
            _transaction(
                operation=OperationType.buy,
                quantity=10,
                price=10,
                tx_date=date(2024, 1, 2),
                asset_type="ETF",
            ),
            _transaction(
                operation=OperationType.sell,
                quantity=10,
                price=12,
                tx_date=date(2024, 2, 2),
                asset_type="ETF",
            ),
            _transaction(
                operation=OperationType.buy,
                quantity=5,
                price=30,
                tx_date=date(2024, 3, 2),
                asset_type="ETF",
            ),
            _transaction(
                operation=OperationType.sell,
                quantity=5,
                price=32,
                tx_date=date(2024, 4, 2),
                asset_type="ETF",
            ),
        ]
    )

    ganhos = await calc_ganhos_capital(db, 1, 2024)

    assert ganhos[0].vendas[0].custo_aquisicao == 10
    assert ganhos[1].vendas[0].custo_aquisicao == 30


@pytest.mark.asyncio
async def test_calc_ganhos_capital_separates_months_and_rounds_values():
    db = _db_with_transactions(
        current_year=[
            _transaction(
                ticker="BOVA11",
                operation=OperationType.buy,
                quantity=3,
                price=10.005,
                fees=0.015,
                tx_date=date(2024, 1, 2),
                asset_type="ETF",
            ),
            _transaction(
                ticker="BOVA11",
                operation=OperationType.sell,
                quantity=1,
                price=11.019,
                fees=0.004,
                tx_date=date(2024, 5, 2),
                asset_type="ETF",
            ),
            _transaction(
                ticker="BOVA11",
                operation=OperationType.sell,
                quantity=1,
                price=9.001,
                fees=0.006,
                tx_date=date(2024, 6, 2),
                asset_type="ETF",
            ),
        ]
    )

    ganhos = await calc_ganhos_capital(db, 1, 2024)

    assert [month.mes for month in ganhos] == ["2024-05", "2024-06"]
    assert ganhos[0].vendas[0].preco_venda == 11.02
    assert ganhos[0].vendas[0].custo_aquisicao == 10.01
    assert ganhos[0].vendas[0].lucro_bruto == 1.01
    assert ganhos[1].vendas[0].preco_venda == 9.0
    assert ganhos[1].vendas[0].lucro_bruto == -1.02


@pytest.mark.asyncio
async def test_calc_ganhos_capital_preserves_current_uncompensated_monthly_loss():
    db = _db_with_transactions(
        current_year=[
            _transaction(
                operation=OperationType.buy,
                quantity=10,
                price=20,
                tx_date=date(2024, 1, 2),
                asset_type="ETF",
            ),
            _transaction(
                operation=OperationType.sell,
                quantity=10,
                price=10,
                tx_date=date(2024, 2, 2),
                asset_type="ETF",
            ),
            _transaction(
                operation=OperationType.buy,
                quantity=10,
                price=10,
                tx_date=date(2024, 3, 2),
                asset_type="ETF",
            ),
            _transaction(
                operation=OperationType.sell,
                quantity=10,
                price=20,
                tx_date=date(2024, 4, 2),
                asset_type="ETF",
            ),
        ]
    )

    ganhos = await calc_ganhos_capital(db, 1, 2024)

    assert ganhos[0].lucro_bruto == -100
    assert ganhos[0].base_calculo == 0
    assert ganhos[1].lucro_bruto == 100
    assert ganhos[1].base_calculo == 100
    assert ganhos[1].ir_devido_swing == 15


@pytest.mark.asyncio
async def test_calc_rendimentos_no_dividends():
    db = AsyncMock(spec=AsyncSession)
    with patch(
        "app.services.irpf_tax_service.load_portfolio_dividend_entitlements",
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
        value_per_unit=Decimal(1),
        currency=currency,
    )
    right = DividendEntitlement(
        event_id=event_id,
        reason=reason,
        entitlement_date=event.record_date,
        eligible_quantity=Decimal(100),
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
        "app.services.irpf_tax_service.load_portfolio_dividend_entitlements",
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
        "app.services.irpf_tax_service.load_portfolio_dividend_entitlements",
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
    from app.services.irpf_tax_service import _detect_day_trades

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
