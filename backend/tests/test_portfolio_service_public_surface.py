from __future__ import annotations

from pathlib import Path


SERVICE_PATH = Path("app/services/portfolio_service.py")


def test_portfolio_service_keeps_public_contracts_used_by_router() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    required = {
        "async def get_portfolio(",
        "async def update_portfolio(",
        "async def get_asset_distribution(",
        "async def invalidate_portfolio_cache(",
        "async def list_portfolios(",
        "async def create_portfolio(",
    }

    missing = sorted(token for token in required if token not in source)
    assert missing == []


def test_portfolio_service_fx_runtime_remains_db_first() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "app.services.fx_service" not in source
    assert "load_latest_usd_brl_rate" in source
    assert "load_usd_brl_rates_for_dates" in source
    assert "cotação USD-BRL persistida indisponível" in source
    assert "cobertura USD-BRL persistida indisponível" in source
