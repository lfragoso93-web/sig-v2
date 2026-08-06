"""Protege tabelas migradas ausentes do agregador ORM contra remoção automática."""

from __future__ import annotations

from pathlib import Path

from app.governance.alembic_metadata_drift_policy import (
    DRIFT_POLICY_RULES,
    LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION,
)

_MODELS_INIT = Path(__file__).resolve().parents[1] / "app" / "models" / "__init__.py"
_ENV = Path(__file__).resolve().parents[1] / "alembic" / "env.py"


def test_alembic_uses_the_explicit_models_aggregator() -> None:
    source = _ENV.read_text(encoding="utf-8")

    assert "import app.models" in source
    assert "target_metadata = Base.metadata" in source


def test_legacy_schema_objects_are_not_silently_reintroduced_as_current_models() -> None:
    source = _MODELS_INIT.read_text(encoding="utf-8").lower()

    for legacy_object in LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION:
        assert legacy_object not in source


def test_legacy_schema_objects_require_an_explicit_decision_before_removal() -> None:
    assert LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION == (
        "fx_rates",
        "irpf_records",
        "irpf_losses",
        "goal_allocations",
    )
    assert "do_not_remove_tables_only_because_absent_from_metadata" in DRIFT_POLICY_RULES
