from types import SimpleNamespace
from typing import cast

from app.models.transaction import OperationType, Transaction
from app.services.ticker_change_processor import calculate_position_at_event


def _tx(operation: OperationType, quantity: float, price: float, fees: float = 0.0) -> Transaction:
    return cast(Transaction, SimpleNamespace(
        operation=operation,
        quantity=quantity,
        price=price,
        fees=fees,
        asset_type="ACAO",
        currency="BRL",
    ))


def test_calcula_saldo_parcial_preservando_custo_medio() -> None:
    position = calculate_position_at_event([
        _tx(OperationType.buy, 100, 10, 10),
        _tx(OperationType.sell, 40, 12),
    ])

    assert position.quantity == 60
    assert round(position.total_cost, 2) == 606.00
    assert round(position.average_price, 2) == 10.10


def test_venda_total_nao_gera_saldo_para_converter() -> None:
    position = calculate_position_at_event([
        _tx(OperationType.buy, 100, 10),
        _tx(OperationType.sell, 100, 12),
    ])

    assert position.quantity == 0
    assert position.total_cost == 0
    assert position.average_price == 0


def test_multiplas_compras_mantem_custo_total() -> None:
    position = calculate_position_at_event([
        _tx(OperationType.buy, 10, 8),
        _tx(OperationType.buy, 10, 12),
    ])

    assert position.quantity == 20
    assert position.total_cost == 200
    assert position.average_price == 10
