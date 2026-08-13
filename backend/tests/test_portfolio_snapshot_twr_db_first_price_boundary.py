from __future__ import annotations

import inspect

from app.services import portfolio_snapshot_twr_service


def test_snapshot_twr_uses_persisted_price_reader_only() -> None:
    source = inspect.getsource(portfolio_snapshot_twr_service)

    assert "app.services.price_history_service" not in source
    assert "await get_prices_at_date_batch(" not in source
    assert "app.services.persisted_price_query_service" in source
    assert "get_persisted_prices_at_date_batch" in source
