from decimal import Decimal

from app.services.twr_service import (
    append_compounded_return_pct,
    calculate_daily_twr_pct,
    compound_return_pcts,
)


def test_aporte_nao_vira_rentabilidade() -> None:
    result = calculate_daily_twr_pct(
        10_000,
        15_000,
        net_external_flow=5_000,
    )

    assert result == Decimal("0.000000")


def test_retirada_nao_vira_prejuizo() -> None:
    result = calculate_daily_twr_pct(
        10_000,
        8_000,
        net_external_flow=-2_000,
    )

    assert result == Decimal("0.000000")


def test_provento_entra_como_retorno() -> None:
    result = calculate_daily_twr_pct(
        10_000,
        10_000,
        dividends_day=100,
    )

    assert result == Decimal("1.000000")


def test_valorizacao_de_mercado_entra_como_retorno() -> None:
    result = calculate_daily_twr_pct(10_000, 10_200)

    assert result == Decimal("2.000000")


def test_retorno_diario_combina_fluxo_provento_e_mercado() -> None:
    result = calculate_daily_twr_pct(
        10_000,
        15_100,
        net_external_flow=5_000,
        dividends_day=100,
    )

    assert result == Decimal("2.000000")


def test_primeiro_dia_sem_base_retorna_zero() -> None:
    result = calculate_daily_twr_pct(0, 1_000)

    assert result == Decimal("0")


def test_retorno_mensal_e_composto_nao_somado() -> None:
    result = compound_return_pcts([2, -1])

    assert result == Decimal("0.980000")


def test_retorno_acumulado_desde_inicio() -> None:
    result = compound_return_pcts([5, -2, 3])

    assert result == Decimal("5.987000")


def test_append_preserva_composicao_incremental() -> None:
    january = append_compounded_return_pct(0, 5)
    february = append_compounded_return_pct(january, -2)
    march = append_compounded_return_pct(february, 3)

    assert january == Decimal("5.000000")
    assert february == Decimal("2.900000")
    assert march == Decimal("5.987000")


def test_lista_vazia_retorna_zero() -> None:
    assert compound_return_pcts([]) == Decimal("0")
