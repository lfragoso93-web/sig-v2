from datetime import date, timedelta
import io
import json
from pathlib import Path

import pytest

from app.cli.build_treasury_standard_calendar_candidate import (
    main as build_candidate_main,
)
from app.cli.plan_market_calendar_promotion import main
from app.services.market_calendar_promotion_plan import (
    build_market_calendar_promotion_plan,
    build_treasury_standard_calendar_candidate,
)


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


def _ordinary_rule():
    b3_source = {
        "reference": "https://www.b3.com.br/calendar-2026",
        "sha256": "b" * 64,
    }
    treasury_source = {
        "reference": "https://tesourodireto.com.br/regras",
        "sha256": "c" * 64,
    }
    return {
        "schema_version": "market-calendar-ordinary-rule.v1",
        "market": "TESOURO_DIRETO_STANDARD",
        "year": 2026,
        "source_documents": [b3_source, treasury_source],
        "ordinary_day_source_reference": treasury_source["reference"],
        "closed_dates": [
            {"date": "2026-01-01", "source_reference": b3_source["reference"]}
        ],
        "special_operation_dates": [
            {"date": "2026-02-18", "source_reference": b3_source["reference"]}
        ],
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


def test_builds_complete_candidate_from_reviewed_ordinary_rule() -> None:
    candidate = build_treasury_standard_calendar_candidate(_ordinary_rule())
    days = {day["date"]: day for day in candidate["days"]}

    assert len(days) == 365
    assert days["2026-01-01"]["is_business_day"] is False
    assert days["2026-01-02"]["is_business_day"] is True
    assert days["2026-01-03"]["is_business_day"] is False
    assert days["2026-02-18"]["is_business_day"] is True
    assert build_market_calendar_promotion_plan(candidate).promotable is True


def test_rejects_ordinary_rule_with_conflicting_exception_types() -> None:
    ordinary_rule = _ordinary_rule()
    ordinary_rule["special_operation_dates"].append(
        {
            "date": "2026-01-01",
            "source_reference": "https://www.b3.com.br/calendar-2026",
        }
    )

    with pytest.raises(ValueError, match="cannot overlap"):
        build_treasury_standard_calendar_candidate(ordinary_rule)


def test_candidate_builder_cli_does_not_access_database(
    monkeypatch,
    capsys,
) -> None:
    payload = json.dumps(_ordinary_rule())

    def open_rule(*_, **__) -> io.StringIO:
        return io.StringIO(payload)

    monkeypatch.setattr(Path, "open", open_rule)
    monkeypatch.setattr("sys.argv", ["build", "reviewed-rule.json"])

    assert build_candidate_main() == 0
    candidate = json.loads(capsys.readouterr().out)
    assert candidate["schema_version"] == "market-calendar-candidate.v1"
    assert len(candidate["days"]) == 365


def test_reviewed_treasury_2026_rule_remains_promotable() -> None:
    rule_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "market-calendar-tesouro-2026-rule.json"
    )
    ordinary_rule = json.loads(rule_path.read_text(encoding="utf-8"))

    candidate = build_treasury_standard_calendar_candidate(ordinary_rule)
    plan = build_market_calendar_promotion_plan(candidate)
    days = {day["date"]: day for day in candidate["days"]}

    assert len(days) == 365
    assert sum(day["is_business_day"] for day in candidate["days"]) == 247
    assert days["2026-02-16"]["is_business_day"] is False
    assert days["2026-02-18"]["is_business_day"] is True
    assert plan.promotable is True
    assert plan.dry_run is True
    assert plan.database_writes_executed == 0
