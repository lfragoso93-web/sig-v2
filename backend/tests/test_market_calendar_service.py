from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.market_calendar_service import (
    MarketCalendarCoverageError,
    add_certified_business_days,
)


def _result(rows):
    result = MagicMock()
    result.all.return_value = rows
    return result


@pytest.mark.asyncio
async def test_uses_persisted_calendar_facts_for_d_plus_two() -> None:
    db = AsyncMock()
    db.execute.return_value = _result(
        [
            (date(2026, 1, 1), False),
            (date(2026, 1, 2), True),
            (date(2026, 1, 3), False),
            (date(2026, 1, 4), False),
            (date(2026, 1, 5), True),
        ]
    )
    assert await add_certified_business_days(db, market="TESOURO_DIRETO", start=date(2025, 12, 31), count=2) == date(2026, 1, 5)


@pytest.mark.asyncio
async def test_fails_closed_when_calendar_date_is_missing() -> None:
    db = AsyncMock()
    db.execute.return_value = _result([(date(2026, 1, 2), True)])
    with pytest.raises(MarketCalendarCoverageError, match="2026-01-01"):
        await add_certified_business_days(db, market="TESOURO_DIRETO", start=date(2025, 12, 31), count=2)
