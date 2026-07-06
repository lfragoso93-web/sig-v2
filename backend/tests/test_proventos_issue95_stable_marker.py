from datetime import date

from app.services.proventos_service import _calc_net_qty
from app.models.transaction import OperationType


def test_issue95_calc_net_qty_ignora_compras_apos_data_com():
    txs = [(date(2024, 1, 10), OperationType.buy, 100)]
    assert _calc_net_qty(txs, date(2024, 1, 1)) == 0.0
