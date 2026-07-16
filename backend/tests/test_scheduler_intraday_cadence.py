"""Contrato da cadência intradiária de cotações."""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.scheduler import _intraday_quote_triggers


TZ = ZoneInfo("America/Sao_Paulo")


def _next_times(start: datetime, count: int) -> list[str]:
    triggers = _intraday_quote_triggers()
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


def test_intraday_quotes_run_every_90_minutes_on_business_days() -> None:
    start = datetime(2026, 7, 13, 8, 59, tzinfo=TZ)  # segunda-feira

    assert _next_times(start, 7) == [
        "2026-07-13 09:00",
        "2026-07-13 10:30",
        "2026-07-13 12:00",
        "2026-07-13 13:30",
        "2026-07-13 15:00",
        "2026-07-13 16:30",
        "2026-07-13 18:00",
    ]


def test_intraday_quotes_skip_weekends() -> None:
    start = datetime(2026, 7, 17, 18, 1, tzinfo=TZ)  # sexta-feira

    assert _next_times(start, 1) == ["2026-07-20 09:00"]
