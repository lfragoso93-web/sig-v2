"""Políticas operacionais compartilhadas pelo domínio de Rentabilidade."""

from datetime import UTC, date, datetime


def utc_today() -> date:
    """Return the current calendar date derived from an explicit UTC clock."""
    return datetime.now(UTC).date()
