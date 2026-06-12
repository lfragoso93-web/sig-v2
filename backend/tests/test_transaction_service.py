"""Testes para a lógica pura de _calc_average_price em transaction_service."""
import pytest
from unittest.mock import MagicMock

from app.models.transaction import TransactionType
from app.services.transaction_service import _calc_average_price


def _mock_db(rows: list[tuple]) -> MagicMock:
    """
    Monta um db síncrono fake que retorna `rows` para .all().
    Cada row: (transaction_type, quantity, price_brl, price)
    """
    row_objects = []
    for tx_type, qty, price_brl, price in rows:
        r = MagicMock()
        r.transaction_type = tx_type
        r.quantity = qty
        r.price_brl = price_brl
        r.price = price
        row_objects.append(r)

    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = row_objects
    return db


class TestCalcAveragePrice:

    def test_compra_simples(self):
        db = _mock_db([
            (TransactionType.COMPRA, 10, 30.0, 30.0),
        ])
        avg = _calc_average_price(db, portfolio_id=1, asset_id=1)
        assert avg == pytest.approx(30.0)

    def test_duas_compras_media_ponderada(self):
        """(10*20 + 10*30) / 20 = 25.0"""
        db = _mock_db([
            (TransactionType.COMPRA, 10, 20.0, 20.0),
            (TransactionType.COMPRA, 10, 30.0, 30.0),
        ])
        avg = _calc_average_price(db, portfolio_id=1, asset_id=1)
        assert avg == pytest.approx(25.0)

    def test_venda_parcial_nao_altera_preco_medio(self):
        """PM = 25. Venda de 5 unidades não muda PM."""
        db = _mock_db([
            (TransactionType.COMPRA, 10, 20.0, 20.0),
            (TransactionType.COMPRA, 10, 30.0, 30.0),
            (TransactionType.VENDA,  5, 40.0, 40.0),
        ])
        avg = _calc_average_price(db, portfolio_id=1, asset_id=1)
        assert avg == pytest.approx(25.0)

    def test_venda_total_retorna_zero(self):
        db = _mock_db([
            (TransactionType.COMPRA, 10, 50.0, 50.0),
            (TransactionType.VENDA,  10, 60.0, 60.0),
        ])
        avg = _calc_average_price(db, portfolio_id=1, asset_id=1)
        assert avg == pytest.approx(0.0)

    def test_bonificacao_aumenta_quantidade_sem_custo(self):
        """Bonificação: qtd aumenta, mas sem custo adicional → PM cai."""
        db = _mock_db([
            (TransactionType.COMPRA,      10, 50.0, 50.0),  # custo 500
            (TransactionType.BONIFICACAO,  5,  0.0,  0.0),  # custo 0
        ])
        avg = _calc_average_price(db, portfolio_id=1, asset_id=1)
        # 500 / 15 ≈ 33.33
        assert avg == pytest.approx(500 / 15, abs=0.01)

    def test_sem_transacoes_retorna_zero(self):
        db = _mock_db([])
        avg = _calc_average_price(db, portfolio_id=1, asset_id=1)
        assert avg == 0.0

    def test_usa_price_brl_quando_disponivel(self):
        """Ativos USD: usa price_brl (em BRL) em vez de price (em USD)."""
        db = _mock_db([
            (TransactionType.COMPRA, 2, 300.0, 60.0),  # price_brl=300, price=60 (USD)
        ])
        avg = _calc_average_price(db, portfolio_id=1, asset_id=1)
        assert avg == pytest.approx(300.0)  # deve usar BRL

    def test_venda_superior_a_estoque_nao_estoura(self):
        """Venda com qty > estoque não deve gerar qty ou cost negativos."""
        db = _mock_db([
            (TransactionType.COMPRA, 5,  10.0, 10.0),
            (TransactionType.VENDA,  10, 15.0, 15.0),  # vende mais do que tem
        ])
        avg = _calc_average_price(db, portfolio_id=1, asset_id=1)
        assert avg == pytest.approx(0.0)
        # e não levanta exceção
