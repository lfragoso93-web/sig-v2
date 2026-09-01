"""Funções puras para rentabilidade ponderada pelo tempo (TWR)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable


_ZERO = Decimal("0")
_HUNDRED = Decimal("100")
_RETURN_QUANT = Decimal("0.000001")


@dataclass(frozen=True)
class DailyTwrInput:
    """Linha diaria ja valorada por fonte historica dedicada."""

    reference_date: date
    market_value: object
    net_external_flow: object = 0
    income_day: object = 0
    has_coverage: bool = True


@dataclass(frozen=True)
class DailyTwrPoint:
    """Resultado diario fail-closed para cadeias TWR dedicadas."""

    reference_date: date
    market_value: Decimal
    net_external_flow: Decimal
    income_day: Decimal
    daily_return_pct: Decimal | None
    accumulated_return_pct: Decimal | None
    available: bool
    status: str
    reason: str | None = None


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


def build_daily_twr_chain(rows: Iterable[DailyTwrInput]) -> list[DailyTwrPoint]:
    """Monta uma cadeia diaria TWR a partir de valores historicos dedicados.

    A funcao e propositalmente fail-closed: linhas sem cobertura nao recebem
    fallback de custo, curva nominal ou provider em tempo de leitura. O chamador
    deve persistir/fornecer a valoracao diaria antes de pedir TWR.
    """
    ordered = sorted(rows, key=lambda row: row.reference_date)
    seen_dates: set[date] = set()
    points: list[DailyTwrPoint] = []
    previous_value = _ZERO
    accumulated_return_pct = _ZERO
    chain_available = True

    for row in ordered:
        if row.reference_date in seen_dates:
            duplicate_date = row.reference_date.isoformat()
            raise ValueError(f"duplicate_twr_reference_date:{duplicate_date}")
        seen_dates.add(row.reference_date)

        market_value = _decimal(row.market_value)
        external_flow = _decimal(row.net_external_flow)
        income = _decimal(row.income_day)

        if not row.has_coverage:
            chain_available = False
            points.append(
                DailyTwrPoint(
                    reference_date=row.reference_date,
                    market_value=market_value,
                    net_external_flow=external_flow,
                    income_day=income,
                    daily_return_pct=None,
                    accumulated_return_pct=None,
                    available=False,
                    status="dedicated_history_not_available",
                    reason="daily_market_value_coverage_missing",
                )
            )
            previous_value = market_value
            continue

        if not chain_available:
            points.append(
                DailyTwrPoint(
                    reference_date=row.reference_date,
                    market_value=market_value,
                    net_external_flow=external_flow,
                    income_day=income,
                    daily_return_pct=None,
                    accumulated_return_pct=None,
                    available=False,
                    status="dedicated_history_interrupted",
                    reason="prior_daily_market_value_coverage_missing",
                )
            )
            previous_value = market_value
            continue

        daily_return_pct = calculate_daily_twr_pct(
            previous_value,
            market_value,
            net_external_flow=external_flow,
            dividends_day=income,
        )
        accumulated_return_pct = append_compounded_return_pct(
            accumulated_return_pct,
            daily_return_pct,
        )
        points.append(
            DailyTwrPoint(
                reference_date=row.reference_date,
                market_value=market_value,
                net_external_flow=external_flow,
                income_day=income,
                daily_return_pct=daily_return_pct,
                accumulated_return_pct=accumulated_return_pct,
                available=True,
                status="available",
            )
        )
        previous_value = market_value

    return points
