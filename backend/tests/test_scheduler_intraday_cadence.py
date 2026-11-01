"""Contrato da cadência intradiária de cotações."""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.scheduler import (
    _crypto_offhours_quote_triggers,
    _intraday_quote_triggers,
)


TZ = ZoneInfo("America/Sao_Paulo")


def _next_times(start: datetime, count: int) -> list[str]:
    current = start
    result: list[datetime] = []
    for _ in range(count):
        candidates = [
            trigger.get_next_fire_time(None, current)
            for trigger in _intraday_quote_triggers()
        ]
        next_fire = min(candidate for candidate in candidates if candidate is not None)
        result.append(next_fire)
        current = next_fire.replace(second=1)
    return [item.strftime("%Y-%m-%d %H:%M") for item in result]


def test_market_quotes_run_hourly_during_business_hours() -> None:
    start = datetime(2026, 7, 13, 8, 59, tzinfo=TZ)  # segunda-feira

    assert _next_times(start, 10) == [
        "2026-07-13 09:00",
        "2026-07-13 10:00",
        "2026-07-13 11:00",
        "2026-07-13 12:00",
        "2026-07-13 13:00",
        "2026-07-13 14:00",
        "2026-07-13 15:00",
        "2026-07-13 16:00",
        "2026-07-13 17:00",
        "2026-07-13 18:00",
    ]


def test_intraday_quotes_skip_weekends() -> None:
    start = datetime(2026, 7, 17, 18, 1, tzinfo=TZ)  # sexta-feira

    assert _next_times(start, 1) == ["2026-07-20 09:00"]


def _next_crypto_times(start: datetime, count: int) -> list[str]:
    triggers = _crypto_offhours_quote_triggers()
    current = start
    result: list[datetime] = []
    for _ in range(count):
        candidates = [
            trigger.get_next_fire_time(None, current)
            for trigger in triggers
        ]
        next_fire = min(candidate for candidate in candidates if candidate is not None)
        result.append(next_fire)
        current = next_fire.replace(second=1)
    return [item.strftime("%Y-%m-%d %H:%M") for item in result]


def test_crypto_quotes_run_hourly_outside_market_hours_and_on_weekends() -> None:
    weekday_start = datetime(2026, 7, 13, 18, 1, tzinfo=TZ)
    weekend_start = datetime(2026, 7, 18, 0, 1, tzinfo=TZ)

    assert _next_crypto_times(weekday_start, 3) == [
        "2026-07-13 19:00",
        "2026-07-13 20:00",
        "2026-07-13 21:00",
    ]
    assert _next_crypto_times(weekend_start, 3) == [
        "2026-07-18 01:00",
        "2026-07-18 02:00",
        "2026-07-18 03:00",
    ]
