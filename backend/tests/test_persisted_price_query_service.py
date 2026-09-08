from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.asset import AssetType
from app.services.persisted_price_query_service import (
    get_persisted_price_history,
    get_persisted_prices_at_date_batch,
)


@pytest.mark.asyncio
async def test_get_persisted_prices_at_date_batch_matches_ticker_case_insensitively() -> None:
    asset_rows = SimpleNamespace(
        all=lambda: [
            SimpleNamespace(id=10, ticker="tesouro-renda-mais-2065"),
        ]
    )
    price_rows = SimpleNamespace(
        scalars=lambda: SimpleNamespace(
            all=lambda: [
                SimpleNamespace(asset_id=10, close=183.24),
            ]
        )
    )
    db = AsyncMock()
    db.execute.side_effect = [asset_rows, price_rows]

    prices = await get_persisted_prices_at_date_batch(
        db,
        [("TESOURO-RENDA-MAIS-2065", AssetType.TESOURO_DIRETO)],
        "2026-09-08",
    )

    assert prices == {"TESOURO-RENDA-MAIS-2065": 183.24}


@pytest.mark.asyncio
async def test_get_persisted_price_history_matches_ticker_case_insensitively() -> None:
    asset_id = SimpleNamespace(scalar_one_or_none=lambda: 10)
    history_rows = SimpleNamespace(
        all=lambda: [
            SimpleNamespace(
                timestamp=datetime(2026, 9, 8, tzinfo=timezone.utc),
                close=183.24,
            )
        ]
    )
    db = AsyncMock()
    db.execute.side_effect = [asset_id, history_rows]

    history = await get_persisted_price_history(db, "TESOURO-RENDA-MAIS-2065")

    assert history == [{"date": "2026-09-08", "price": 183.24}]
