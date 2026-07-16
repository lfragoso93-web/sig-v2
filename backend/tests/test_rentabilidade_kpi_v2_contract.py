from pydantic import ValidationError
import pytest

from app.schemas.rentabilidade import RentabilidadeKpisResponse


def _payload() -> dict:
    return {
        "contract_version": "rentabilidade.v2",
        "patrimonio_atual": 12000.0,
        "custo_posicoes_abertas": 10000.0,
        "resultado_nao_realizado": 1500.0,
        "resultado_realizado": 200.0,
        "resultado_total": 1800.0,
        "proventos_total": 100.0,
        "proventos_12m": 80.0,
        "twr_dia_pct": None,
        "twr_mes_pct": None,
        "twr_12m_pct": None,
        "twr_desde_inicio_pct": None,
        "valuation_updated_at": "2026-07-16T15:00:00-03:00",
        "performance_as_of": None,
        "proventos_as_of": "2026-07-16",
        "return_is_estimated": True,
        "has_partial_prices": False,
        "price_coverage_pct": 100.0,
        "performance_source": "unavailable",
    }


def test_contract_accepts_unavailable_twr_without_fake_zero() -> None:
    model = RentabilidadeKpisResponse.model_validate(_payload())
    assert model.twr_mes_pct is None
    assert model.twr_desde_inicio_pct is None
    assert model.performance_source == "unavailable"


def test_contract_rejects_legacy_aliases() -> None:
    payload = _payload()
    payload["retorno_total_pct"] = 18.0
    with pytest.raises(ValidationError):
        RentabilidadeKpisResponse.model_validate(payload)


def test_contract_exposes_distinct_result_components() -> None:
    model = RentabilidadeKpisResponse.model_validate(_payload())
    assert model.resultado_nao_realizado == 1500.0
    assert model.resultado_realizado == 200.0
    assert model.proventos_total == 100.0
    assert model.resultado_total == 1800.0
