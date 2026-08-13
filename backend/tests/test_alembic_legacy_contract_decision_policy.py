"""Protege decisões provisórias para contratos legados fora do ORM atual."""

from __future__ import annotations

from pathlib import Path

from app.governance.alembic_metadata_drift_policy import (
    GOAL_CONSUMER_RULES,
    LEGACY_CONTRACT_DECISION_RULES,
    LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_GOAL_ROUTER = _BACKEND_ROOT / "app" / "routers" / "goals.py"
_GOAL_SERVICE = _BACKEND_ROOT / "app" / "services" / "goals_service.py"
_MODELS_INIT = _BACKEND_ROOT / "app" / "models" / "__init__.py"


def test_fx_rates_is_current_and_goal_allocations_remains_explicit_decision() -> None:
    assert "fx_rates" not in LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION
    assert "goal_allocations" in LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION


def test_current_fx_contract_and_legacy_goal_policy_are_explicit() -> None:
    assert "fx_rates_is_current_persisted_contract" in LEGACY_CONTRACT_DECISION_RULES
    assert "goal_allocations_preserved_until_goal_consumers_are_inventory_complete" in (
        LEGACY_CONTRACT_DECISION_RULES
    )


def test_goal_allocations_has_no_current_runtime_surface() -> None:
    runtime_source = "\n".join(
        (
            _GOAL_ROUTER.read_text(encoding="utf-8"),
            _GOAL_SERVICE.read_text(encoding="utf-8"),
            _MODELS_INIT.read_text(encoding="utf-8"),
        )
    ).lower()

    assert "goal_allocations_has_no_runtime_consumer_evidence" in GOAL_CONSUMER_RULES
    assert "goal_allocations_is_not_exposed_by_current_goal_router_or_service" in (
        GOAL_CONSUMER_RULES
    )
    assert "goal_allocation" not in runtime_source
    assert "goal_allocations" not in runtime_source


def test_goal_allocations_removal_requires_database_evidence() -> None:
    assert "goal_allocations_requires_data_fixture_before_removal" in GOAL_CONSUMER_RULES
    assert "goal_allocations_requires_row_count_and_fk_inventory_before_removal" in (
        GOAL_CONSUMER_RULES
    )
    assert "do_not_reintroduce_goal_allocations_orm_only_for_alembic_check" in (
        GOAL_CONSUMER_RULES
    )


def test_alembic_drift_cannot_drive_model_reintroduction_or_table_drop() -> None:
    assert "do_not_reintroduce_orm_models_only_to_silence_alembic_check" in (
        LEGACY_CONTRACT_DECISION_RULES
    )
    assert "do_not_drop_legacy_tables_without_domain_decision_and_synthetic_fixture" in (
        LEGACY_CONTRACT_DECISION_RULES
    )
