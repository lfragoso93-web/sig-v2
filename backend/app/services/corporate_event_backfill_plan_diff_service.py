"""Comparação offline de planos read-only de backfill corporativo."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CorporateEventBackfillPlanDiff:
    equal: bool
    count_changes: dict[str, tuple[object, object]]
    entry_changes: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["count_changes"] = {
            key: {"before": values[0], "after": values[1]}
            for key, values in self.count_changes.items()
        }
        return payload


_COUNT_FIELDS = (
    "total",
    "reconcile_only",
    "backfill_candidate",
    "manual_review",
    "blocked_review",
)


def _entries_by_id(plan: dict[str, Any]) -> dict[int, dict[str, object]]:
    entries = plan.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("entries must be a list")

    indexed: dict[int, dict[str, object]] = {}
    for raw in entries:
        if not isinstance(raw, dict):
            raise ValueError("each entry must be an object")
        event_id = raw.get("event_id")
        if not isinstance(event_id, int):
            raise ValueError("entry event_id must be an integer")
        if event_id in indexed:
            raise ValueError(f"duplicate event_id: {event_id}")
        indexed[event_id] = raw
    return indexed


def compare_corporate_event_backfill_plans(
    before: dict[str, Any],
    after: dict[str, Any],
) -> CorporateEventBackfillPlanDiff:
    """Compara dois planos já gerados sem acessar banco ou providers."""

    count_changes: dict[str, tuple[object, object]] = {}
    for field in _COUNT_FIELDS:
        left = before.get(field)
        right = after.get(field)
        if left != right:
            count_changes[field] = (left, right)

    before_entries = _entries_by_id(before)
    after_entries = _entries_by_id(after)
    changes: list[dict[str, object]] = []

    for event_id in sorted(set(before_entries) | set(after_entries)):
        left = before_entries.get(event_id)
        right = after_entries.get(event_id)
        if left == right:
            continue
        if left is None:
            change_type = "added"
        elif right is None:
            change_type = "removed"
        else:
            change_type = "changed"
        changes.append(
            {
                "event_id": event_id,
                "change_type": change_type,
                "before": left,
                "after": right,
            }
        )

    return CorporateEventBackfillPlanDiff(
        equal=not count_changes and not changes,
        count_changes=count_changes,
        entry_changes=tuple(changes),
    )
