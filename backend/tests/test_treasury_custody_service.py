from datetime import date
from unittest.mock import ANY, AsyncMock

import pytest

import app.services.treasury_custody_service as custody_service
from app.services.market_calendar_service import MarketCalendarCoverageError


@pytest.mark.asyncio
async def test_resolves_d_plus_two_with_standard_market_calendar(
    monkeypatch,
) -> None:
    add_days = AsyncMock(return_value=date(2026, 1, 5))
    monkeypatch.setattr(
        custody_service, "add_certified_business_days", add_days
    )

    result = await custody_service.resolve_conservative_treasury_custody_date(
        AsyncMock(),
        transaction_date=date(2025, 12, 31),
    )

    assert result == date(2026, 1, 5)
    add_days.assert_awaited_once_with(
        ANY,
        market="TESOURO_DIRETO_STANDARD",
        start=date(2025, 12, 31),
        count=2,
    )


@pytest.mark.asyncio
async def test_preserves_missing_calendar_coverage(
    monkeypatch,
) -> None:
    add_days = AsyncMock(
        side_effect=MarketCalendarCoverageError("calendar coverage missing")
    )
    monkeypatch.setattr(
        custody_service, "add_certified_business_days", add_days
    )

    with pytest.raises(MarketCalendarCoverageError, match="coverage missing"):
        await custody_service.resolve_conservative_treasury_custody_date(
            AsyncMock(), transaction_date=date(2025, 12, 31)
        )
