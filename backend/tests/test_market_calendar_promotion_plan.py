from datetime import date, timedelta
import io
import json
from pathlib import Path

import pytest

from app.services.market_calendar_promotion_plan import (
    build_market_calendar_promotion_plan,
)
from app.cli.plan_market_calendar_promotion import main


_SOURCE = {
    "reference": "https://www.b3.com.br/calendar-2026",
    "sha256": "a" * 64,
}


def _candidate(*, omit: date | None = None, duplicate: bool = False):
    current = date(2026, 1, 1)
    end = date(2027, 1, 1)
    days = []
    while current < end:
        if current != omit:
            days.append(
                {
                    "date": current.isoformat(),
                    "is_business_day": current.weekday() < 5,
                    "source_reference": _SOURCE["reference"],
                }
            )
        current += timedelta(days=1)
    if duplicate:
        days.append(days[0].copy())
    return {
        "schema_version": "market-calendar-candidate.v1",
        "market": "TESOURO_DIRETO_STANDARD",
        "year": 2026,
        "source_documents": [_SOURCE],
        "days": days,
    }


def test_builds_promotable_plan_for_complete_daily_candidate() -> None:
    plan = build_market_calendar_promotion_plan(_candidate())

    assert plan.promotable is True
    assert plan.dry_run is True
    assert plan.database_writes_executed == 0
    assert plan.expected_days == 365
    assert plan.supplied_days == 365


def test_blocks_candidate_when_daily_coverage_is_incomplete() -> None:
    plan = build_market_calendar_promotion_plan(
        _candidate(omit=date(2026, 6, 4))
    )

    assert plan.promotable is False
    assert plan.blockers == (
        "incomplete_daily_coverage:missing=1:first=2026-06-04",
    )


def test_blocks_duplicate_calendar_day_even_when_the_value_matches() -> None:
    plan = build_market_calendar_promotion_plan(_candidate(duplicate=True))

    assert plan.promotable is False
    assert plan.blockers == ("duplicate_calendar_date:2026-01-01",)


def test_rejects_candidate_with_unknown_schema() -> None:
    candidate = _candidate()
    candidate["schema_version"] = "unknown"

    with pytest.raises(ValueError, match="unsupported"):
        build_market_calendar_promotion_plan(candidate)


def test_cli_returns_nonzero_plan_without_database_writes(
    monkeypatch,
    capsys,
) -> None:
    candidate_payload = json.dumps(_candidate(omit=date(2026, 6, 4)))

    def open_candidate(*_, **__) -> io.StringIO:
        return io.StringIO(candidate_payload)

    monkeypatch.setattr(Path, "open", open_candidate)
    monkeypatch.setattr(
        "sys.argv",
        ["plan", "reviewed-candidate.json"],
    )

    assert main() == 2
    payload = json.loads(capsys.readouterr().out)

    assert payload["dry_run"] is True
    assert payload["database_writes_executed"] == 0
    assert payload["promotable"] is False
