"""Protege tabelas migradas ausentes do agregador ORM contra remoção automática."""

from __future__ import annotations

from pathlib import Path

_MODELS_INIT = Path(__file__).resolve().parents[1] / "app" / "models" / "__init__.py"
_ENV = Path(__file__).resolve().parents[1] / "alembic" / "env.py"

_LEGACY_SCHEMA_OBJECTS = (
    "fx_rates",
    "irpf_records",
    "irpf_losses",
    "goal_allocations",
)


def test_alembic_uses_the_explicit_models_aggregator() -> None:
    source = _ENV.read_text(encoding="utf-8")

    assert "import app.models" in source
    assert "target_metadata = Base.metadata" in source


def test_legacy_schema_objects_are_not_silently_reintroduced_as_current_models() -> None:
    source = _MODELS_INIT.read_text(encoding="utf-8").lower()

    for legacy_object in _LEGACY_SCHEMA_OBJECTS:
        assert legacy_object not in source


def test_legacy_schema_objects_require_an_explicit_decision_before_removal() -> None:
    inventory = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "ALEMBIC_METADATA_DRIFT_INVENTORY_2026-08.md"
    ).read_text(encoding="utf-8").lower()

    for legacy_object in _LEGACY_SCHEMA_OBJECTS:
        assert f"`{legacy_object}`" in inventory

    assert "não remover tabelas apenas porque estão ausentes" in inventory
