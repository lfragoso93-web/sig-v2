"""Caracterização de bordas contábeis ainda presentes no serviço fiscal."""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.models.transaction import OperationType
from app.services.irpf_tax_service import _get_usd_brl_rate, calc_ganhos_capital
from tests.irpf_characterization_helpers import db_with_transactions, transaction


@pytest.mark.asyncio
async def test_sale_above_position_uses_average_cost_for_the_full_sale():
    """Congela a projeção local vigente; vender acima da posição não é validado."""

    db = db_with_transactions(
        current_year=[
            transaction(
                ticker="BOVA11",
                operation=OperationType.buy,
                quantity=10,
                price=10,
                tx_date=date(2024, 1, 2),
            ),
            transaction(
                ticker="BOVA11",
                operation=OperationType.sell,
                quantity=15,
                price=20,
                tx_date=date(2024, 2, 2),
            ),
        ]
    )

    month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert month.vendas[0].quantidade == 15
    assert month.vendas[0].custo_aquisicao == 10
    assert month.total_custo == 150
    assert month.lucro_swing_trade == 150
    assert month.base_calculo == 150


@pytest.mark.asyncio
async def test_international_operations_convert_each_transaction_at_its_date():
    db = db_with_transactions(
        current_year=[
            transaction(
                ticker="IVVB11-USD",
                asset_type="ETF_INTERNACIONAL",
                currency="USD",
                operation=OperationType.buy,
                quantity=10,
                price=10,
                tx_date=date(2024, 3, 1),
            ),
            transaction(
                ticker="IVVB11-USD",
                asset_type="ETF_INTERNACIONAL",
                currency="USD",
                operation=OperationType.sell,
                quantity=10,
                price=12,
                tx_date=date(2024, 4, 1),
            ),
        ]
    )

    with patch(
        "app.services.irpf_tax_service._get_usd_brl_rate",
        new=AsyncMock(side_effect=[5.0, 6.0]),
    ) as get_rate:
        month = (await calc_ganhos_capital(db, 1, 2024))[0]

    assert [call.args[1] for call in get_rate.await_args_list] == [
        date(2024, 3, 1),
        date(2024, 4, 1),
    ]
    assert all(call.args[0] is db for call in get_rate.await_args_list)
    assert month.vendas[0].preco_venda == 72
    assert month.vendas[0].custo_aquisicao == 50
    assert month.total_vendas == 720
    assert month.total_custo == 500
    assert month.lucro_swing_trade == 220
    assert month.ir_devido_swing == 33


@pytest.mark.asyncio
async def test_exchange_rate_uses_persisted_db_first_reader():
    db = AsyncMock()
    with patch(
        "app.services.irpf_tax_service.get_persisted_usd_brl_rate_for_date",
        new=AsyncMock(return_value=5.25),
    ) as get_rate:
        rate = await _get_usd_brl_rate(db, date(2024, 5, 2))

    assert rate == 5.25
    get_rate.assert_awaited_once_with(db, date(2024, 5, 2))


@pytest.mark.asyncio
async def test_missing_exchange_rate_propagates_persisted_coverage_failure():
    db = AsyncMock()
    with patch(
        "app.services.irpf_tax_service.get_persisted_usd_brl_rate_for_date",
        new=AsyncMock(side_effect=RuntimeError("cobertura USD-BRL indisponível")),
    ):
        with pytest.raises(RuntimeError, match="cobertura USD-BRL indisponível"):
            await _get_usd_brl_rate(db, date(2024, 5, 2))


@pytest.mark.asyncio
async def test_capital_gains_queries_only_transactions_in_current_boundary():
    db = db_with_transactions(current_year=[])

    assert await calc_ganhos_capital(db, 1, 2024) == []
    assert db.execute.await_count == 2
    assert all(
        "transactions" in str(call.args[0]).lower()
        for call in db.execute.await_args_list
    )
