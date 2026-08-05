"""Caracteriza o plano read-only de backfill do legado corporativo."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from app.services.corporate_event_legacy_backfill_plan_service import (
    LegacyBackfillAction,
    plan_legacy_corporate_event_backfill,
)

_SERVICE = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "corporate_event_legacy_backfill_plan_service.py"
)
_CLI = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "cli"
    / "plan_corporate_event_legacy_backfill.py"
)


def _event(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "id": 9,
        "ticker": "ABCD3",
        "event_type": "DESDOBRAMENTO",
        "status": "PENDENTE",
        "portfolio_id": None,
        "source_event_id": "legacy:9",
        "brapi_event_id": None,
        "effective_date": date(2026, 1, 10),
        "event_date": date(2026, 1, 10),
        "quantity_factor": Decimal("2"),
        "ratio": Decimal("2"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_complete_event_requires_only_reconciliation() -> None:
    entry = plan_legacy_corporate_event_backfill(_event())

    assert entry.action is LegacyBackfillAction.RECONCILE_ONLY
    assert entry.proposed_updates == {}
    assert entry.blockers == ()


def test_missing_canonical_fields_use_only_deterministic_legacy_aliases() -> None:
    entry = plan_legacy_corporate_event_backfill(
        _event(
            source_event_id=None,
            brapi_event_id="brapi:123",
            effective_date=None,
            event_date=date(2020, 5, 4),
            quantity_factor=None,
            ratio=Decimal("1.5"),
        )
    )

    assert entry.action is LegacyBackfillAction.BACKFILL_CANDIDATE
    assert entry.proposed_updates == {
        "source_event_id": "brapi:123",
        "effective_date": "2020-05-04",
        "quantity_factor": "1.5",
    }
    assert entry.blockers == ()


def test_missing_legacy_aliases_requires_manual_review() -> None:
    entry = plan_legacy_corporate_event_backfill(
        _event(
            effective_date=None,
            event_date=None,
            quantity_factor=None,
            ratio=None,
        )
    )

    assert entry.action is LegacyBackfillAction.MANUAL_REVIEW
    assert entry.blockers == ("missing:event_date", "missing:ratio")


def test_portfolio_bound_event_is_never_planned_for_write() -> None:
    entry = plan_legacy_corporate_event_backfill(_event(portfolio_id=4))

    assert entry.action is LegacyBackfillAction.BLOCKED_REVIEW
    assert entry.proposed_updates == {}
    assert entry.blockers == ("portfolio_bound",)


def test_service_and_cli_are_strictly_read_only() -> None:
    source = (_SERVICE.read_text(encoding="utf-8") + _CLI.read_text(encoding="utf-8")).lower()

    for forbidden in (
        ".commit(",
        ".delete(",
        ".add(",
        "update(corporateevent",
        "delete(corporateevent",
        "requests",
        "httpx",
        "yahoo",
        "brapi_client",
    ):
        assert forbidden not in source

    cli_source = _CLI.read_text(encoding="utf-8")
    assert '"corporate-event-legacy-backfill-plan.v1"' in cli_source
    assert '"writes_executed": False' in cli_source
