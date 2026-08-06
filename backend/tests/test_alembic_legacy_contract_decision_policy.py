"""Protege decisões provisórias para contratos legados fora do ORM atual."""

from __future__ import annotations

from app.governance.alembic_metadata_drift_policy import (
    LEGACY_CONTRACT_DECISION_RULES,
    LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION,
)


def test_fx_rates_is_current_and_goal_allocations_remains_explicit_decision() -> None:
    assert "fx_rates" not in LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION
    assert "goal_allocations" in LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION


def test_current_fx_contract_and_legacy_goal_policy_are_explicit() -> None:
    assert "fx_rates_is_current_persisted_contract" in LEGACY_CONTRACT_DECISION_RULES
    assert "goal_allocations_preserved_until_goal_consumers_are_inventory_complete" in (
        LEGACY_CONTRACT_DECISION_RULES
    )


def test_alembic_drift_cannot_drive_model_reintroduction_or_table_drop() -> None:
    assert "do_not_reintroduce_orm_models_only_to_silence_alembic_check" in (
        LEGACY_CONTRACT_DECISION_RULES
    )
    assert "do_not_drop_legacy_tables_without_domain_decision_and_synthetic_fixture" in (
        LEGACY_CONTRACT_DECISION_RULES
    )
