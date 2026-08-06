"""Protege contratos migrados contra remoção ou classificação ORM incorreta."""

from __future__ import annotations

from pathlib import Path

from app.governance.alembic_metadata_drift_policy import (
    CURRENT_PERSISTED_SCHEMA_OBJECTS,
    DRIFT_POLICY_RULES,
    LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_MODELS_INIT = _BACKEND_ROOT / "app" / "models" / "__init__.py"
_FX_MODEL = _BACKEND_ROOT / "app" / "models" / "fx_rate.py"
_ENV = _BACKEND_ROOT / "alembic" / "env.py"


def test_alembic_uses_the_explicit_models_aggregator() -> None:
    source = _ENV.read_text(encoding="utf-8")

    assert "import app.models" in source
    assert "target_metadata = Base.metadata" in source


def test_current_persisted_schema_objects_are_registered_in_metadata() -> None:
    source = _MODELS_INIT.read_text(encoding="utf-8")

    assert CURRENT_PERSISTED_SCHEMA_OBJECTS == ("fx_rates",)
    assert "from app.models.fx_rate import FxRate" in source
    assert '"FxRate"' in source


def test_fx_rate_model_preserves_persisted_index_contract() -> None:
    source = _FX_MODEL.read_text(encoding="utf-8")

    assert 'Index("ix_fx_rates_pair_date", "pair", "rate_date")' in source
    assert 'Index("idx_fx_pair_date_desc", "pair", desc("rate_date"))' in source
    assert 'UniqueConstraint("pair", "rate_date", name="uq_fx_rates_pair_date")' in source


def test_legacy_schema_objects_are_not_silently_reintroduced_as_current_models() -> None:
    source = _MODELS_INIT.read_text(encoding="utf-8").lower()

    for legacy_object in LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION:
        assert legacy_object not in source


def test_legacy_schema_objects_require_an_explicit_decision_before_removal() -> None:
    assert LEGACY_SCHEMA_OBJECTS_REQUIRING_DECISION == (
        "irpf_records",
        "irpf_losses",
        "goal_allocations",
    )
    assert "do_not_remove_tables_only_because_absent_from_metadata" in DRIFT_POLICY_RULES
