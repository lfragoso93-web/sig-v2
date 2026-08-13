from __future__ import annotations

import inspect

from app.services import portfolio_service


def test_portfolio_service_uses_persisted_price_readers_only() -> None:
    source = inspect.getsource(portfolio_service)

    assert "app.services.quotes_service" not in source
    assert "app.services.price_history_service" not in source
    assert "get_prices(" not in source
    assert "await get_prices_at_date_batch(" not in source
    assert "get_persisted_current_prices" in source
    assert "get_persisted_prices_at_date_batch" in source
