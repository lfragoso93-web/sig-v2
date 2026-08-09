from pathlib import Path


SERVICES = (
    Path("app/services/portfolio_service.py"),
    Path("app/services/portfolio_canonical_valuation_service.py"),
)


def test_financial_runtime_does_not_import_legacy_fx_service() -> None:
    findings: list[str] = []
    for path in SERVICES:
        source = path.read_text(encoding="utf-8")
        if "app.services.fx_service" in source:
            findings.append(str(path))
    assert findings == []


def test_financial_runtime_requires_persisted_fx_coverage() -> None:
    canonical = Path(
        "app/services/portfolio_canonical_valuation_service.py"
    ).read_text(encoding="utf-8")
    portfolio = Path("app/services/portfolio_service.py").read_text(encoding="utf-8")

    assert "load_usd_brl_rate_at_or_before" in canonical
    assert "cobertura USD-BRL persistida indisponível" in canonical

    assert "load_usd_brl_rates_for_dates" in portfolio
    assert "load_latest_usd_brl_rate" in portfolio
    assert "cobertura USD-BRL persistida indisponível" in portfolio
    assert "cotação USD-BRL persistida indisponível" in portfolio
