"""Caracterização da segregação fiscal Day Trade/Swing Trade vigente.

Os cenários deste módulo congelam o comportamento atual antes de qualquer
correção fiscal ou integração com a projeção contábil canônica.
"""

from datetime import date

import pytest

from app.models.transaction import OperationType
from app.services.irpf_tax_service import calc_ganhos_capital
from tests.irpf_characterization_helpers import (
    db_with_transactions as _db_with_transactions,
)
from tests.irpf_characterization_helpers import transaction as _transaction


@pytest.mark.asyncio
async def test_intraday_remainder_is_swing_trade_on_the_following_day():
    db = _db_with_transactions(
        current_year=[
            _transaction(
                ticker="BOVA11",
                operation=OperationType.buy,
                quantity=20,
                price=10,
                tx_date=date(2024, 5, 2),
            ),
            _transaction(
                ticker="BOVA11",
                operation=OperationType.sell,
                quantity=5,
                price=12,
                tx_date=date(2024, 5, 2),
            ),
            _transaction(
                ticker="BOVA11",
                operation=OperationType.sell,
                quantity=15,
                price=14,
                tx_date=date(2024, 5, 3),
            ),
        ]
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert [sale.is_day_trade for sale in month.vendas] == [True, False]
    assert [sale.lucro_bruto for sale in month.vendas] == [10, 60]
    assert month.lucro_day_trade == 10
    assert month.lucro_swing_trade == 60
    assert month.base_calculo == 70
    assert month.ir_devido_day_trade == 2
    assert month.ir_devido_swing == 9


@pytest.mark.asyncio
async def test_interleaved_same_day_operations_use_the_running_average_cost():
    db = _db_with_transactions(
        current_year=[
            _transaction(
                ticker="BOVA11",
                operation=OperationType.buy,
                quantity=10,
                price=10,
                tx_date=date(2024, 6, 3),
            ),
            _transaction(
                ticker="BOVA11",
                operation=OperationType.sell,
                quantity=4,
                price=12,
                tx_date=date(2024, 6, 3),
            ),
            _transaction(
                ticker="BOVA11",
                operation=OperationType.buy,
                quantity=10,
                price=14,
                tx_date=date(2024, 6, 3),
            ),
            _transaction(
                ticker="BOVA11",
                operation=OperationType.sell,
                quantity=16,
                price=15,
                tx_date=date(2024, 6, 3),
            ),
        ]
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert [sale.is_day_trade for sale in month.vendas] == [True, True]
    assert [sale.custo_aquisicao for sale in month.vendas] == [10, 12.5]
    assert [sale.lucro_bruto for sale in month.vendas] == [8, 40]
    assert month.lucro_day_trade == 48
    assert month.ir_devido_day_trade == 9.6


@pytest.mark.asyncio
async def test_day_trade_detection_is_isolated_by_ticker():
    db = _db_with_transactions(
        current_year=[
            _transaction(
                ticker="BOVA11",
                operation=OperationType.buy,
                quantity=10,
                price=10,
                tx_date=date(2024, 7, 3),
            ),
            _transaction(
                ticker="SMAL11",
                operation=OperationType.buy,
                quantity=10,
                price=20,
                tx_date=date(2024, 7, 3),
            ),
            _transaction(
                ticker="BOVA11",
                operation=OperationType.sell,
                quantity=10,
                price=8,
                tx_date=date(2024, 7, 4),
            ),
            _transaction(
                ticker="SMAL11",
                operation=OperationType.sell,
                quantity=10,
                price=25,
                tx_date=date(2024, 7, 4),
            ),
            _transaction(
                ticker="BOVA11",
                operation=OperationType.buy,
                quantity=1,
                price=9,
                tx_date=date(2024, 7, 4),
            ),
        ]
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert [(sale.ticker, sale.is_day_trade) for sale in month.vendas] == [
        ("BOVA11", True),
        ("SMAL11", False),
    ]
    assert month.lucro_day_trade == -20
    assert month.lucro_swing_trade == 50
    assert month.base_calculo == 50
    assert month.ir_devido_day_trade == 0
    assert month.ir_devido_swing == 7.5
