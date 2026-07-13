"""Funções puras para rentabilidade ponderada pelo tempo (TWR)."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_RETURN_QUANT = Decimal("0.000001")


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or 0))


def _percent(value: Decimal) -> Decimal:
    return value.quantize(_RETURN_QUANT, rounding=ROUND_HALF_UP)


def calculate_daily_twr_pct(
    previous_value: object,
    current_value: object,
    *,
    net_external_flow: object = 0,
    dividends_day: object = 0,
) -> Decimal:
    """Calcula o retorno diário em percentual.

    ``current_value`` representa, nesta fase, somente o valor de mercado dos
    ativos. Por isso os proventos recebidos no dia são adicionados explicitamente.
    Quando o SGI passar a manter saldo de caixa dentro do patrimônio, o chamador
    deverá enviar ``dividends_day=0`` para não contar o rendimento duas vezes.

    O fluxo externo líquido segue a convenção:
      - aporte: positivo;
      - retirada: negativo.
    """
    previous = _decimal(previous_value)
    if previous <= 0:
        return _ZERO

    current = _decimal(current_value)
    external_flow = _decimal(net_external_flow)
    dividends = _decimal(dividends_day)
    rate = ((current + dividends - external_flow) / previous) - Decimal("1")
    return _percent(rate * _HUNDRED)


def compound_return_pcts(returns: Iterable[object]) -> Decimal:
    """Compõe retornos percentuais sem somá-los aritmeticamente."""
    factor = Decimal("1")
    found = False
    for value in returns:
        rate_pct = _decimal(value)
        factor *= Decimal("1") + rate_pct / _HUNDRED
        found = True
    if not found:
        return _ZERO
    return _percent((factor - Decimal("1")) * _HUNDRED)


def append_compounded_return_pct(
    accumulated_return_pct: object,
    daily_return_pct: object,
) -> Decimal:
    """Acrescenta um retorno diário ao acumulado já composto."""
    return compound_return_pcts((accumulated_return_pct, daily_return_pct))
