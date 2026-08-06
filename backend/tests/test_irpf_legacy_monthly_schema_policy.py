"""Protege a fronteira entre o IRPF canônico e o schema mensal legado."""

from __future__ import annotations

from pathlib import Path

from app.governance.alembic_metadata_drift_policy import IRPF_LEGACY_SCHEMA_RULES

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_APP_ROOT = _BACKEND_ROOT / "app"
_INITIAL_SCHEMA = _BACKEND_ROOT / "alembic" / "versions" / "001_initial_schema.py"
_RUNTIME_DIRS = (
    _APP_ROOT / "models",
    _APP_ROOT / "routers",
    _APP_ROOT / "services",
)
_LEGACY_TABLES = ("irpf_records", "irpf_losses")


def test_initial_migration_preserves_legacy_monthly_irpf_tables() -> None:
    source = _INITIAL_SCHEMA.read_text(encoding="utf-8")

    for table in _LEGACY_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in source
        assert f"DROP TABLE IF EXISTS {table}" in source


def test_current_runtime_has_no_legacy_monthly_table_consumers() -> None:
    findings: list[str] = []

    for directory in _RUNTIME_DIRS:
        for path in sorted(directory.rglob("*.py")):
            source = path.read_text(encoding="utf-8").lower()
            for table in _LEGACY_TABLES:
                if table in source:
                    findings.append(
                        f"{path.relative_to(_APP_ROOT)} references {table}"
                    )

    assert findings == []


def test_legacy_monthly_irpf_decision_requires_data_evidence() -> None:
    assert IRPF_LEGACY_SCHEMA_RULES == (
        "irpf_records_and_losses_are_migrated_legacy_contracts",
        "current_irpf_runtime_must_not_read_or_write_legacy_monthly_tables",
        "legacy_monthly_tables_require_row_count_and_fk_inventory",
        "legacy_monthly_tables_require_synthetic_fixture_before_removal",
        "do_not_reintroduce_legacy_irpf_orm_models_for_alembic_check",
        "coordinate_destructive_decision_with_issue_56_and_issue_241",
    )
