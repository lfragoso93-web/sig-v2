"""Caracteriza a elegibilidade do catálogo para projeções financeiras."""

from types import SimpleNamespace

from app.services.corporate_action_position_reader import _is_projection_eligible


def _event(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "status": "PENDENTE",
        "source_provider": "brapi",
        "is_canonical": True,
        "reconciliation_status": "MATCHED",
        "requires_review": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_matched_reviewed_canonical_event_is_eligible() -> None:
    assert _is_projection_eligible(_event()) is True


def test_unreconciled_event_is_not_eligible() -> None:
    assert (
        _is_projection_eligible(_event(reconciliation_status="UNRECONCILED"))
        is False
    )


def test_conflicting_event_is_not_eligible() -> None:
    assert _is_projection_eligible(_event(reconciliation_status="CONFLICT")) is False


def test_noncanonical_evidence_is_not_eligible() -> None:
    assert _is_projection_eligible(_event(is_canonical=False)) is False


def test_event_requiring_review_is_not_eligible() -> None:
    assert _is_projection_eligible(_event(requires_review=True)) is False


def test_global_legacy_event_remains_eligible_during_contraction() -> None:
    assert (
        _is_projection_eligible(
            _event(
                source_provider="legacy",
                reconciliation_status="UNRECONCILED",
                requires_review=True,
            )
        )
        is True
    )


def test_ignored_legacy_event_is_not_eligible() -> None:
    assert (
        _is_projection_eligible(
            _event(
                source_provider="legacy",
                status="IGNORADO",
                reconciliation_status="UNRECONCILED",
                requires_review=True,
            )
        )
        is False
    )
