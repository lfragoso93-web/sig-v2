"""Caracteriza a política dry-run do legado de eventos corporativos."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.services.corporate_event_legacy_dry_run_service import (
    LegacyCorporateEventDisposition,
    classify_legacy_corporate_event,
)

_SERVICE = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "corporate_event_legacy_dry_run_service.py"
)


def _event(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "id": 7,
        "ticker": "ABCD3",
        "event_type": "DESDOBRAMENTO",
        "source_event_id": "legacy:7",
        "effective_date": object(),
        "quantity_factor": 2,
        "portfolio_id": None,
        "status": "PENDENTE",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_complete_global_event_is_reconcilable() -> None:
    result = classify_legacy_corporate_event(_event())

    assert result.disposition is LegacyCorporateEventDisposition.RECONCILABLE
    assert result.reasons == ("canonical_fields_complete",)


def test_missing_canonical_fields_are_incomplete_before_review_policy() -> None:
    result = classify_legacy_corporate_event(
        _event(
            source_event_id=None,
            effective_date=None,
            portfolio_id=3,
        )
    )

    assert result.disposition is LegacyCorporateEventDisposition.INCOMPLETE
    assert result.reasons == (
        "missing:source_event_id",
        "missing:effective_date",
    )


def test_portfolio_bound_or_ignored_event_is_blocked_for_review() -> None:
    result = classify_legacy_corporate_event(
        _event(portfolio_id=3, status="IGNORADO")
    )

    assert result.disposition is LegacyCorporateEventDisposition.BLOCKED_REVIEW
    assert result.reasons == ("portfolio_bound", "ignored")


def test_dry_run_service_has_no_write_operations() -> None:
    source = _SERVICE.read_text(encoding="utf-8").lower()

    for forbidden in (
        ".commit(",
        ".delete(",
        ".add(",
        "update(corporateevent",
        "delete(corporateevent",
    ):
        assert forbidden not in source
