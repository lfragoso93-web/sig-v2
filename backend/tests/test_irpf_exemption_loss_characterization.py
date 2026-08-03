"""Caracterização da isenção e dos prejuízos mensais no IRPF vigente."""

from datetime import date

import pytest

from app.models.transaction import OperationType
from app.services.irpf_tax_service import calc_ganhos_capital
from tests.irpf_characterization_helpers import db_with_transactions, transaction


def _buy_and_sell(
    *,
    ticker: str,
    asset_type: str,
    quantity: float,
    buy_price: float,
    sell_price: float,
    month: int,
) -> list:
    return [
        transaction(
            ticker=ticker,
            asset_type=asset_type,
            operation=OperationType.buy,
            quantity=quantity,
            price=buy_price,
            tx_date=date(2024, month, 1),
        ),
        transaction(
            ticker=ticker,
            asset_type=asset_type,
            operation=OperationType.sell,
            quantity=quantity,
            price=sell_price,
            tx_date=date(2024, month, 2),
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("total_sales", "expected_exemption"),
    [(19_999.0, 19_999.0), (20_000.0, 20_000.0)],
)
async def test_stock_sales_at_or_below_limit_are_fully_exempt(
    total_sales: float,
    expected_exemption: float,
):
    db = db_with_transactions(
        current_year=_buy_and_sell(
            ticker="VALE3",
            asset_type="ACAO",
            quantity=100,
            buy_price=100,
            sell_price=total_sales / 100,
            month=1,
        )
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert month.total_vendas == total_sales
    assert month.isencao_aplicada == expected_exemption
    assert month.base_calculo == 0
    assert month.ir_devido_swing == 0
    assert month.vendas[0].is_isento is True


@pytest.mark.asyncio
async def test_stock_sales_above_limit_are_taxed_on_the_profit():
    db = db_with_transactions(
        current_year=_buy_and_sell(
            ticker="VALE3",
            asset_type="ACAO",
            quantity=100,
            buy_price=100,
            sell_price=200.01,
            month=2,
        )
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert month.total_vendas == 20_001
    assert month.lucro_swing_trade == 10_001
    assert month.isencao_aplicada == 0
    assert month.base_calculo == 10_001
    assert month.ir_devido_swing == 1_500.15
    assert month.vendas[0].is_isento is False


@pytest.mark.asyncio
@pytest.mark.parametrize("asset_type", ["ETF", "FII"])
async def test_non_stock_classes_do_not_receive_monthly_exemption(asset_type: str):
    db = db_with_transactions(
        current_year=_buy_and_sell(
            ticker=f"ATIVO-{asset_type}",
            asset_type=asset_type,
            quantity=100,
            buy_price=100,
            sell_price=150,
            month=3,
        )
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert month.total_vendas == 15_000
    assert month.isencao_aplicada == 0
    assert month.base_calculo == 5_000
    assert month.ir_devido_swing == 750
    assert month.vendas[0].is_isento is False


@pytest.mark.asyncio
async def test_stock_limit_is_aggregated_across_tickers():
    db = db_with_transactions(
        current_year=[
            *_buy_and_sell(
                ticker="VALE3",
                asset_type="ACAO",
                quantity=100,
                buy_price=50,
                sell_price=110,
                month=4,
            ),
            *_buy_and_sell(
                ticker="PETR4",
                asset_type="ACAO",
                quantity=100,
                buy_price=50,
                sell_price=100,
                month=4,
            ),
        ]
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert month.total_vendas == 21_000
    assert month.lucro_swing_trade == 11_000
    assert month.isencao_aplicada == 0
    assert month.base_calculo == 11_000
    assert month.ir_devido_swing == 1_650
    assert all(sale.is_isento is False for sale in month.vendas)


@pytest.mark.asyncio
async def test_swing_loss_is_not_carried_to_a_later_profit_in_current_behavior():
    db = db_with_transactions(
        current_year=[
            *_buy_and_sell(
                ticker="BOVA11",
                asset_type="ETF",
                quantity=100,
                buy_price=100,
                sell_price=50,
                month=5,
            ),
            *_buy_and_sell(
                ticker="SMAL11",
                asset_type="ETF",
                quantity=100,
                buy_price=50,
                sell_price=100,
                month=6,
            ),
        ]
    )

    loss_month, profit_month = await calc_ganhos_capital(db, 1, 2024)

    assert loss_month.lucro_swing_trade == -5_000
    assert loss_month.base_calculo == 0
    assert loss_month.ir_devido_swing == 0
    assert profit_month.lucro_swing_trade == 5_000
    assert profit_month.base_calculo == 5_000
    assert profit_month.ir_devido_swing == 750


@pytest.mark.asyncio
async def test_day_trade_loss_is_not_carried_to_a_later_profit():
    db = db_with_transactions(
        current_year=[
            transaction(
                ticker="BOVA11",
                operation=OperationType.buy,
                quantity=100,
                price=100,
                tx_date=date(2024, 7, 1),
            ),
            transaction(
                ticker="BOVA11",
                operation=OperationType.sell,
                quantity=100,
                price=50,
                tx_date=date(2024, 7, 1),
            ),
            transaction(
                ticker="SMAL11",
                operation=OperationType.buy,
                quantity=100,
                price=50,
                tx_date=date(2024, 8, 1),
            ),
            transaction(
                ticker="SMAL11",
                operation=OperationType.sell,
                quantity=100,
                price=100,
                tx_date=date(2024, 8, 1),
            ),
        ]
    )

    loss_month, profit_month = await calc_ganhos_capital(db, 1, 2024)

    assert loss_month.lucro_day_trade == -5_000
    assert loss_month.base_calculo == 0
    assert loss_month.ir_devido_day_trade == 0
    assert profit_month.lucro_day_trade == 5_000
    assert profit_month.base_calculo == 5_000
    assert profit_month.ir_devido_day_trade == 1_000


@pytest.mark.asyncio
async def test_exempt_stock_sales_currently_reduce_other_swing_class_base():
    """Congela a agregação cruzada vigente; não valida a regra fiscal."""

    db = db_with_transactions(
        current_year=[
            *_buy_and_sell(
                ticker="VALE3",
                asset_type="ACAO",
                quantity=100,
                buy_price=50,
                sell_price=60,
                month=9,
            ),
            *_buy_and_sell(
                ticker="BOVA11",
                asset_type="ETF",
                quantity=100,
                buy_price=50,
                sell_price=55,
                month=9,
            ),
        ]
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert month.lucro_swing_trade == 1_500
    assert month.isencao_aplicada == 6_000
    assert month.base_calculo == 0
    assert month.ir_devido_swing == 0
    assert [sale.is_isento for sale in month.vendas] == [True, False]


@pytest.mark.asyncio
async def test_bdr_is_in_the_current_stock_exemption_group():
    db = db_with_transactions(
        current_year=_buy_and_sell(
            ticker="AAPL34",
            asset_type="BDR",
            quantity=100,
            buy_price=100,
            sell_price=150,
            month=10,
        )
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert month.total_vendas == 15_000
    assert month.isencao_aplicada == 15_000
    assert month.base_calculo == 0
    assert month.vendas[0].is_isento is True


@pytest.mark.asyncio
async def test_withholding_remains_zero_in_month_and_sale_contracts():
    db = db_with_transactions(
        current_year=_buy_and_sell(
            ticker="BOVA11",
            asset_type="ETF",
            quantity=100,
            buy_price=100,
            sell_price=150,
            month=11,
        )
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert month.ir_retido_fonte == 0
    assert month.vendas[0].ir_retido == 0
    assert month.ir_a_recolher == month.ir_devido_swing
