from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.persisted_current_price_query_service import get_persisted_current_prices


@pytest.mark.asyncio
async def test_get_persisted_current_prices_matches_ticker_case_insensitively() -> None:
    db = AsyncMock()
    result = SimpleNamespace(
        all=lambda: [
            SimpleNamespace(
                ticker="tesouro-renda-mais-2065",
                last_price=183.24,
            )
        ]
    )
    db.execute.return_value = result

    prices = await get_persisted_current_prices(db, ["TESOURO-RENDA-MAIS-2065"])

    assert prices == {"TESOURO-RENDA-MAIS-2065": 183.24}
