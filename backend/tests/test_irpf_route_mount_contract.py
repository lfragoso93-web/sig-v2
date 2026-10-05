from pathlib import Path


def test_irpf_router_exposes_portfolio_scoped_api_contract() -> None:
    source = Path("app/main.py").read_text(encoding="utf-8")

    assert 'prefix=f"{PREFIX}/portfolios",   tags=["irpf"]' in source
    assert 'prefix=f"{PREFIX}/irpf",         tags=["irpf"]' in source
