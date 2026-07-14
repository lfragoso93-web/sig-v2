from app.services.benchmark_rate_service import (
    _DAILY_INCREMENTAL_DAYS,
    _MONTHLY_INCREMENTAL_DAYS,
    _MONTHLY_INDICATORS,
)


def test_indices_mensais_usam_janela_maior():
    assert {"IPCA", "IGPM"}.issubset(_MONTHLY_INDICATORS)
    assert _MONTHLY_INCREMENTAL_DAYS >= 90
    assert _MONTHLY_INCREMENTAL_DAYS > _DAILY_INCREMENTAL_DAYS
