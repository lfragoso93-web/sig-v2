"""Protege a fronteira entre o IRPF canônico e o schema mensal legado."""

from __future__ import annotations

import ast
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
_ALLOWED_INVENTORY_MODULE_PREFIXES = ("pre_prod_inventory",)


def _is_docstring_node(node: ast.AST, parent: ast.AST | None) -> bool:
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Constant):
        return False
    if not isinstance(node.value.value, str):
        return False
    if not isinstance(parent, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return False
    return bool(parent.body) and parent.body[0] is node


def _executable_string_literals(source: str) -> list[str]:
    tree = ast.parse(source)
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    literals: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        parent = parents.get(node)
        expression = parent if isinstance(parent, ast.Expr) else None
        expression_parent = parents.get(expression) if expression is not None else None
        if expression is not None and _is_docstring_node(expression, expression_parent):
            continue
        literals.append(node.value.lower())
    return literals


def test_initial_migration_preserves_legacy_monthly_irpf_tables() -> None:
    source = _INITIAL_SCHEMA.read_text(encoding="utf-8")

    for table in _LEGACY_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in source
        assert f"DROP TABLE IF EXISTS {table}" in source


def test_current_runtime_has_no_legacy_monthly_table_consumers() -> None:
    findings: list[str] = []

    for directory in _RUNTIME_DIRS:
        for path in sorted(directory.rglob("*.py")):
            if path.stem.startswith(_ALLOWED_INVENTORY_MODULE_PREFIXES):
                continue
            source = path.read_text(encoding="utf-8")
            executable_literals = _executable_string_literals(source)
            executable_source = "\n".join(executable_literals)
            for table in _LEGACY_TABLES:
                if table in executable_source:
                    findings.append(
                        f"{path.relative_to(_APP_ROOT)} references {table}"
                    )

    assert findings == []


def test_inventory_references_are_restricted_to_pre_prod_audit_modules() -> None:
    findings: list[str] = []

    services_dir = _APP_ROOT / "services"
    for path in sorted(services_dir.rglob("*.py")):
        source = path.read_text(encoding="utf-8").lower()
        if not any(table in source for table in _LEGACY_TABLES):
            continue
        if path.stem.startswith(_ALLOWED_INVENTORY_MODULE_PREFIXES):
            continue
        if path.name == "user_service.py":
            tree = ast.parse(path.read_text(encoding="utf-8"))
            if not any(
                table in literal
                for literal in _executable_string_literals(path.read_text(encoding="utf-8"))
                for table in _LEGACY_TABLES
            ):
                continue
        findings.append(str(path.relative_to(_APP_ROOT)))

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
