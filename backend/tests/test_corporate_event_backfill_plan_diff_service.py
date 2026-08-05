"""Caracteriza o comparador offline de planos de backfill corporativo."""

from app.services.corporate_event_backfill_plan_diff_service import (
    compare_corporate_event_backfill_plans,
)


def _plan(entries: list[dict[str, object]]) -> dict[str, object]:
    return {
        "total": len(entries),
        "reconcile_only": 0,
        "backfill_candidate": len(entries),
        "manual_review": 0,
        "blocked_review": 0,
        "entries": entries,
    }


def test_equal_plans_produce_empty_diff() -> None:
    plan = _plan([{"event_id": 2, "action": "backfill_candidate"}])

    result = compare_corporate_event_backfill_plans(plan, plan)

    assert result.equal is True
    assert result.count_changes == {}
    assert result.entry_changes == ()


def test_changed_entry_is_reported_in_event_id_order() -> None:
    before = _plan([
        {"event_id": 2, "action": "backfill_candidate"},
        {"event_id": 1, "action": "backfill_candidate"},
    ])
    after = _plan([
        {"event_id": 1, "action": "manual_review"},
        {"event_id": 3, "action": "backfill_candidate"},
    ])

    result = compare_corporate_event_backfill_plans(before, after)

    assert result.equal is False
    assert [item["event_id"] for item in result.entry_changes] == [1, 2, 3]
    assert [item["change_type"] for item in result.entry_changes] == [
        "changed",
        "removed",
        "added",
    ]


def test_duplicate_event_id_is_rejected() -> None:
    duplicate = _plan([
        {"event_id": 1, "action": "backfill_candidate"},
        {"event_id": 1, "action": "manual_review"},
    ])

    try:
        compare_corporate_event_backfill_plans(duplicate, duplicate)
    except ValueError as exc:
        assert "duplicate event_id" in str(exc)
    else:
        raise AssertionError("duplicate event_id should be rejected")
