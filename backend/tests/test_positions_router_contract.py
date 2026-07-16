from unittest.mock import AsyncMock, patch

import pytest

from app.routers.portfolios import portfolio_positions


@pytest.mark.asyncio
async def test_positions_endpoint_uses_canonical_contract():
    expected = [{"label": "Ações", "positions": []}]
    user = type("User", (), {"id": 9})()
    db = AsyncMock()

    with patch(
        "app.routers.portfolios.get_canonical_portfolio_positions",
        new=AsyncMock(return_value=expected),
    ) as service:
        result = await portfolio_positions(3, db=db, current_user=user)

    assert result == expected
    service.assert_awaited_once_with(db, 3, 9)
