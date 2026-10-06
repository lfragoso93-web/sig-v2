"""Canonical injectable clock for date-sensitive domain logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...

    def today(self) -> date: ...


@dataclass(frozen=True, slots=True)
class SystemClock:
    """Wall clock preserving the process-local calendar used by production."""

    def now(self) -> datetime:
        return datetime.now().astimezone()

    def today(self) -> date:
        return self.now().date()


@dataclass(frozen=True, slots=True)
class FrozenClock:
    """Deterministic clock for tests and explicit replay contexts."""

    current: datetime

    def __post_init__(self) -> None:
        if self.current.tzinfo is None or self.current.utcoffset() is None:
            raise ValueError("FrozenClock requires a timezone-aware datetime")

    def now(self) -> datetime:
        return self.current

    def today(self) -> date:
        return self.current.date()


SYSTEM_CLOCK: Clock = SystemClock()
