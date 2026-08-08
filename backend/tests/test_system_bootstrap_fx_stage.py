from pathlib import Path


FX_STAGE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "system_bootstrap_fx_stage.py"
)


def test_fx_bootstrap_reuses_audited_seed_and_max_valid_usd_brl_window() -> None:
    source = FX_STAGE_PATH.read_text(encoding="utf-8")

    assert "run_pre_prod_fx_seed" in source
    assert "validate_fx_seed_identity" in source
    assert "USD_BRL_HISTORY_START_DATE = date(1994, 7, 1)" in source
    assert "StrictPtax" not in source
    assert "AwesomeAPI" not in source
    assert "brapi" not in source.lower()
    assert "yfinance" not in source.lower()


def test_fx_bootstrap_fails_when_audited_seed_is_not_ok() -> None:
    source = FX_STAGE_PATH.read_text(encoding="utf-8")
    assert "if not result.ok:" in source
    assert "achados bloqueantes" in source
