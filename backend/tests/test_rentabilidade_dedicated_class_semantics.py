from app.services.rentabilidade_class_service import class_metric_semantics


def test_treasury_exposes_current_mark_to_market_without_twr_claim() -> None:
    semantics = class_metric_semantics("TESOURO_DIRETO")

    assert semantics["valuation_method"] == "treasury_mark_to_market"
    assert semantics["current_metrics_available"] is True
    assert semantics["dedicated_history_required"] is True
    assert "marcação a mercado" in str(semantics["valuation_label"]).lower()
    assert "TWR" in str(semantics["performance_reason"])


def test_fixed_income_exposes_accrual_without_promoting_income_pct_to_twr() -> None:
    semantics = class_metric_semantics("RENDA_FIXA")

    assert semantics["valuation_method"] == "fixed_income_accrual"
    assert semantics["current_metrics_available"] is True
    assert semantics["dedicated_history_required"] is True
    assert "indexador" in str(semantics["valuation_label"]).lower()
    assert "cadeia diária" in str(semantics["performance_reason"])


def test_market_class_keeps_snapshot_twr_path() -> None:
    semantics = class_metric_semantics("ACAO")

    assert semantics == {
        "valuation_method": "intraday_market_valuation",
        "valuation_label": "Valuation de mercado intradiário",
        "result_label": "Resultado patrimonial atual",
        "current_metrics_available": True,
        "dedicated_history_required": False,
        "performance_reason": None,
    }
