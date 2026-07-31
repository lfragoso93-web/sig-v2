from datetime import UTC, datetime
from types import SimpleNamespace

from app.core.config import Settings
from app.services.corporate_complex_event_execution_service import (
    ComplexEventExecutionIntentStatus,
    build_complex_event_execution_intent,
)
from app.services.corporate_exchange_projection_service import (
    CorporateExchangeProjectionPlan,
)


def _event(**values):
    defaults = {
        "id": 91,
        "status": "VALIDATED",
        "reconciliation_status": "MANUALLY_VALIDATED",
        "reviewed_by_user_id": 1,
        "requires_review": False,
        "reviewed_at": datetime(2026, 7, 31, tzinfo=UTC),
        "economic_identity_hash": "economic-91",
    }
    return SimpleNamespace(**(defaults | values))


def _plan(*, executable: bool = True):
    return CorporateExchangeProjectionPlan(
        event_id=91,
        source_asset_id=7,
        destination_asset_id=8,
        source_quantity_before=100,
        source_quantity_after=0,
        destination_quantity_delta=50,
        destination_fractional_quantity=0,
        total_cost_before=2500,
        allocated_source_cost=0,
        allocated_destination_cost=2500,
        cash_component_total=0,
        cash_treatment=None,
        executable=executable,
        blocking_reasons=() if executable else ("cost_basis_allocation",),
    )


def test_feature_flag_blocks_even_complete_reviewed_plan() -> None:
    intent = build_complex_event_execution_intent(
        _event(), portfolio_id=3, plan=_plan(), execution_enabled=False
    )

    assert intent.status is ComplexEventExecutionIntentStatus.BLOCKED_FEATURE_DISABLED
    assert intent.writable is False
    assert intent.blocking_reasons == ("feature_disabled",)


def test_execution_feature_flag_defaults_to_disabled() -> None:
    assert (
        Settings.model_fields["CORPORATE_COMPLEX_EVENTS_EXECUTION_ENABLED"].default
        is False
    )


def test_idempotency_key_is_stable_for_same_economic_intent() -> None:
    first = build_complex_event_execution_intent(
        _event(), portfolio_id=3, plan=_plan(), execution_enabled=False
    )
    second = build_complex_event_execution_intent(
        _event(), portfolio_id=3, plan=_plan(), execution_enabled=False
    )

    assert first.idempotency_key == second.idempotency_key


def test_unreviewed_event_blocks_before_feature_gate() -> None:
    intent = build_complex_event_execution_intent(
        _event(reviewed_by_user_id=None),
        portfolio_id=3,
        plan=_plan(),
        execution_enabled=True,
    )

    assert intent.status is ComplexEventExecutionIntentStatus.BLOCKED_EVENT_NOT_REVIEWED
    assert intent.writable is False


def test_enabled_gate_only_marks_intent_ready_without_making_it_writable() -> None:
    intent = build_complex_event_execution_intent(
        _event(), portfolio_id=3, plan=_plan(), execution_enabled=True
    )

    assert intent.status is ComplexEventExecutionIntentStatus.READY
    assert intent.writable is False
