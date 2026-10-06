"""Reusable SQLAlchemy query-count assertion for regression tests."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass(frozen=True, slots=True)
class QueryBudgetExceeded(AssertionError):
    actual: int
    maximum: int

    def __str__(self) -> str:
        return f"query budget exceeded: actual={self.actual}, maximum={self.maximum}"


@contextmanager
def assert_max_queries(
    engine: AsyncEngine,
    maximum: int,
) -> Iterator[list[str]]:
    """Capture SQL statements and fail when a tested block exceeds its budget."""

    if maximum < 0:
        raise ValueError("maximum query count cannot be negative")
    statements: list[str] = []

    def capture(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        statements.append(statement.strip())

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        yield statements
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
        if len(statements) > maximum:
            raise QueryBudgetExceeded(len(statements), maximum)
