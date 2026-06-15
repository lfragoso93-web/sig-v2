"""Testes para transaction_service — modelo atual (ticker, operation, date)."""
import pytest
from unittest.mock import MagicMock
from datetime import date

from app.models.transaction import OperationType
from app.services.transaction_service import (
    _calc_average_price,
    _calc_current_quantity,
)


# ---------------------------------------------------------------------------
# Helpers de mock
# ---------------------------------------------------------------------------

def _mock_db_avg(rows: list[tuple]) -> MagicMock:
    """
    Monta db fake para _calc_average_price.
    Cada row: (operation: OperationType, quantity: float, price: float)
    """
    row_objects = []
    for op, qty, price in rows:
        r = MagicMock()
        r.operation = op
        r.quantity = qty
        r.price = price
        row_objects.append(r)

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = row_objects
    return db


def _mock_db_qty(rows: list[tuple]) -> MagicMock:
    """
    Monta db fake para _calc_current_quantity.
    Cada row: (operation: OperationType, quantity: float)
    """
    row_objects = []
    for op, qty in rows:
        r = MagicMock()
        r.operation = op
        r.quantity = qty
        row_objects.append(r)

    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = row_objects
    return db


# ---------------------------------------------------------------------------
# _calc_average_price
# ---------------------------------------------------------------------------

class TestCalcAveragePrice:

    def test_compra_simples(self):
        db = _mock_db_avg([
            (OperationType.buy, 10, 30.0),
        ])
        avg = _calc_average_price(db, portfolio_id=1, ticker="PETR4")
        assert avg == pytest.approx(30.0)

    def test_duas_compras_media_ponderada(self):
        """(10*20 + 10*30) / 20 = 25.0"""
        db = _mock_db_avg([
            (OperationType.buy, 10, 20.0),
            (OperationType.buy, 10, 30.0),
        ])
        avg = _calc_average_price(db, portfolio_id=1, ticker="PETR4")
        assert avg == pytest.approx(25.0)

    def test_venda_parcial_nao_altera_preco_medio(self):
        """PM = 25. Venda de 5 unidades nao muda PM."""
        db = _mock_db_avg([
            (OperationType.buy,  10, 20.0),
            (OperationType.buy,  10, 30.0),
            (OperationType.sell,  5, 40.0),
        ])
        avg = _calc_average_price(db, portfolio_id=1, ticker="PETR4")
        assert avg == pytest.approx(25.0)

    def test_venda_total_retorna_zero(self):
        db = _mock_db_avg([
            (OperationType.buy,  10, 50.0),
            (OperationType.sell, 10, 60.0),
        ])
        avg = _calc_average_price(db, portfolio_id=1, ticker="PETR4")
        assert avg == pytest.approx(0.0)

    def test_sem_transacoes_retorna_zero(self):
        db = _mock_db_avg([])
        avg = _calc_average_price(db, portfolio_id=1, ticker="PETR4")
        assert avg == 0.0

    def test_venda_superior_a_estoque_nao_estoura(self):
        """Venda com qty > estoque nao deve gerar qty ou cost negativos."""
        db = _mock_db_avg([
            (OperationType.buy,   5, 10.0),
            (OperationType.sell, 10, 15.0),
        ])
        avg = _calc_average_price(db, portfolio_id=1, ticker="PETR4")
        assert avg == pytest.approx(0.0)

    def test_multiplas_compras_e_vendas(self):
        """Compra 10@20, compra 10@30 => PM=25. Vende 5@35. Compra 5@40 => PM = (15*25 + 5*40) / 20 = 28.75"""
        db = _mock_db_avg([
            (OperationType.buy,  10, 20.0),
            (OperationType.buy,  10, 30.0),
            (OperationType.sell,  5, 35.0),
            (OperationType.buy,   5, 40.0),
        ])
        avg = _calc_average_price(db, portfolio_id=1, ticker="PETR4")
        assert avg == pytest.approx(28.75)


# ---------------------------------------------------------------------------
# _calc_current_quantity
# ---------------------------------------------------------------------------

class TestCalcCurrentQuantity:

    def test_apenas_compras(self):
        db = _mock_db_qty([
            (OperationType.buy, 10),
            (OperationType.buy, 5),
        ])
        qty = _calc_current_quantity(db, portfolio_id=1, ticker="ITUB4")
        assert qty == pytest.approx(15.0)

    def test_compra_e_venda_parcial(self):
        db = _mock_db_qty([
            (OperationType.buy,  10),
            (OperationType.sell,  3),
        ])
        qty = _calc_current_quantity(db, portfolio_id=1, ticker="ITUB4")
        assert qty == pytest.approx(7.0)

    def test_venda_total_resulta_em_zero(self):
        db = _mock_db_qty([
            (OperationType.buy,  10),
            (OperationType.sell, 10),
        ])
        qty = _calc_current_quantity(db, portfolio_id=1, ticker="ITUB4")
        assert qty == pytest.approx(0.0)

    def test_sem_transacoes_retorna_zero(self):
        db = _mock_db_qty([])
        qty = _calc_current_quantity(db, portfolio_id=1, ticker="ITUB4")
        assert qty == 0.0

    def test_venda_maior_que_estoque_nao_retorna_negativo(self):
        """_calc_current_quantity nao deve retornar valor negativo."""
        db = _mock_db_qty([
            (OperationType.buy,   5),
            (OperationType.sell, 10),
        ])
        qty = _calc_current_quantity(db, portfolio_id=1, ticker="ITUB4")
        assert qty >= 0.0
