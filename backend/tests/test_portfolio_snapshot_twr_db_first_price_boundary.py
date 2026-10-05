from __future__ import annotations

import inspect

from app.services import lifecycle_aware_price_service
from app.services import portfolio_canonical_valuation_service
from app.services import portfolio_snapshot_canonical_twr_service


def test_snapshot_twr_uses_canonical_db_first_price_boundary() -> None:
    snapshot_source = inspect.getsource(portfolio_snapshot_canonical_twr_service)
    valuation_source = inspect.getsource(portfolio_canonical_valuation_service)
    lifecycle_source = inspect.getsource(lifecycle_aware_price_service)

    assert "portfolio_canonical_valuation_service" in snapshot_source
    assert "calculate_canonical_portfolio_totals" in snapshot_source

    assert "lifecycle_aware_price_service" in valuation_source
    assert "get_prices_at_date_with_lifecycle" in valuation_source

    assert "app.models.asset_price" in lifecycle_source
    assert "AssetPrice" in lifecycle_source
    assert "app.services.price_history_service" not in lifecycle_source
    assert "get_prices_at_date_batch" not in lifecycle_source
