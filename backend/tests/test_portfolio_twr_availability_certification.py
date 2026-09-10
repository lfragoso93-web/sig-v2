from pathlib import Path

from app.cli.portfolio_twr_availability_certification import _EXPECTED


def test_synthetic_twr_availability_contract_exposes_fixed_income_available() -> None:
    assert _EXPECTED["RENDA_FIXA"] == (True, "available")
    for asset_type in (
        "ACAO",
        "BDR",
        "CRIPTO",
        "ETF_NACIONAL",
        "FII",
        "TESOURO_DIRETO",
    ):
        assert _EXPECTED[asset_type] == (True, "available")


def test_twr_availability_gate_does_not_materialize_or_call_provider() -> None:
    source = Path("app/cli/portfolio_twr_availability_certification.py").read_text(
        encoding="utf-8"
    )

    assert "class_twr_availability" in source
    assert "load_portfolio_synthetic_certification_fixture" in source
    assert "rf_daily_twr=true" in source
    assert "issue149=closed" in source
    for forbidden in (
        "AsyncSession",
        "db.",
        "provider",
        "rebuild_class_snapshots",
        "backfill",
        "AssetPrice",
    ):
        assert forbidden not in source
