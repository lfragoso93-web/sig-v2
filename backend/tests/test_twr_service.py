from datetime import date
from decimal import Decimal

from app.services.twr_service import (
    DailyTwrInput,
    append_compounded_return_pct,
    build_daily_twr_chain,
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


def test_cadeia_diaria_dedicada_reflete_variacao_de_pu() -> None:
    points = build_daily_twr_chain(
        [
            DailyTwrInput(date(2026, 8, 3), Decimal("1000.00")),
            DailyTwrInput(date(2026, 8, 4), Decimal("1100.00")),
        ]
    )

    assert points[0].daily_return_pct == Decimal("0")
    assert points[0].accumulated_return_pct == Decimal("0.000000")
    assert points[1].daily_return_pct == Decimal("10.000000")
    assert points[1].accumulated_return_pct == Decimal("10.000000")
    assert points[1].status == "available"


def test_cadeia_diaria_dedicada_segrega_aporte_como_fluxo_externo() -> None:
    points = build_daily_twr_chain(
        [
            DailyTwrInput(date(2026, 8, 3), Decimal("1000.00")),
            DailyTwrInput(
                date(2026, 8, 4),
                Decimal("1500.00"),
                net_external_flow=Decimal("500.00"),
            ),
        ]
    )

    assert points[1].daily_return_pct == Decimal("0.000000")
    assert points[1].accumulated_return_pct == Decimal("0.000000")


def test_cadeia_diaria_dedicada_trata_rendimento_como_retorno() -> None:
    points = build_daily_twr_chain(
        [
            DailyTwrInput(date(2026, 8, 3), Decimal("1000.00")),
            DailyTwrInput(
                date(2026, 8, 4),
                Decimal("1000.00"),
                income_day=Decimal("25.00"),
            ),
        ]
    )

    assert points[1].daily_return_pct == Decimal("2.500000")
    assert points[1].accumulated_return_pct == Decimal("2.500000")


def test_cadeia_diaria_dedicada_falha_fechada_sem_cobertura() -> None:
    points = build_daily_twr_chain(
        [
            DailyTwrInput(date(2026, 8, 3), Decimal("1000.00")),
            DailyTwrInput(date(2026, 8, 4), Decimal("1010.00"), has_coverage=False),
            DailyTwrInput(date(2026, 8, 5), Decimal("1020.00")),
        ]
    )

    assert points[1].available is False
    assert points[1].daily_return_pct is None
    assert points[1].status == "dedicated_history_not_available"
    assert points[1].reason == "daily_market_value_coverage_missing"
    assert points[2].available is False
    assert points[2].status == "dedicated_history_interrupted"


def test_cadeia_diaria_dedicada_rejeita_data_duplicada() -> None:
    try:
        build_daily_twr_chain(
            [
                DailyTwrInput(date(2026, 8, 3), Decimal("1000.00")),
                DailyTwrInput(date(2026, 8, 3), Decimal("1010.00")),
            ]
        )
    except ValueError as exc:
        assert str(exc) == "duplicate_twr_reference_date:2026-08-03"
    else:
        raise AssertionError("duplicate date should fail")
