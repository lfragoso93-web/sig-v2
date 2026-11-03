from unittest.mock import AsyncMock, patch

import pytest

from app.routers.portfolios import portfolio_positions
from app.services.portfolio_positions_access_service import READ_PORTFOLIO_POSITIONS


@pytest.mark.asyncio
async def test_positions_endpoint_uses_canonical_contract():
    expected = [{"label": "Ações", "positions": []}]
    user = type("User", (), {"id": 9})()
    db = AsyncMock()

    with patch(
        "app.routers.portfolios.get_authorized_canonical_positions",
        new=AsyncMock(return_value=expected),
    ) as service:
        result = await portfolio_positions(3, db=db, current_user=user)

    assert result == expected
    access = service.await_args.args[1]
    assert access.portfolio_id == 3
    assert access.user_id == 9
    assert access.permissions == frozenset({READ_PORTFOLIO_POSITIONS})
