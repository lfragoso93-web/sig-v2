"""Gate fail-closed para deteccao de deriva Alembic <-> MetaData.

Garante que o MetaData do SQLAlchemy e o schema fisico do banco estejam 100%
alinhados, sem tolerancia a drift (ALLOWED_DRIFT_TABLES = frozenset()).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from alembic.autogenerate import produce_migrations
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401  # registra todos os models no Base.metadata


ALLOWED_DRIFT_TABLES: frozenset[str] = frozenset()


@dataclass(frozen=True)
class DriftInspection:
    tables: frozenset[str]
    unknown_operations: tuple[str, ...]
    operation_descriptions: tuple[str, ...] = ()

    @property
    def has_drift(self) -> bool:
        return bool(self.tables or self.unknown_operations)

    @property
    def is_allowed(self) -> bool:
        return (
            self.has_drift
            and not self.unknown_operations
            and self.tables <= ALLOWED_DRIFT_TABLES
        )


def _operation_children(operation: Any) -> Iterable[Any]:
    children = getattr(operation, "ops", None)
    if children is None:
        return ()
    return tuple(children)


def _describe_leaf_operation(operation: Any, table_name: str | None) -> str:
    parts = [type(operation).__name__]
    if table_name:
        parts.append(f"table={table_name}")
    for attr in ("column_name", "index_name", "constraint_name"):
        value = getattr(operation, attr, None)
        if value:
            parts.append(f"{attr}={value}")
    column = getattr(operation, "column", None)
    column_name = getattr(column, "name", None)
    if column_name:
        parts.append(f"column={column_name}")
    return " ".join(parts)


def inspect_upgrade_operations(operations: Iterable[Any]) -> DriftInspection:
    """Classifica operacoes de autogenerate por tabela, falhando fechado."""

    tables: set[str] = set()
    unknown_operations: list[str] = []
    operation_descriptions: list[str] = []

    def visit(operation: Any, inherited_table: str | None = None) -> None:
        table_name = getattr(operation, "table_name", None) or inherited_table
        children = tuple(_operation_children(operation))

        if table_name:
            tables.add(str(table_name))

        if children:
            next_table = str(table_name) if table_name else inherited_table
            for child in children:
                visit(child, next_table)
            return

        normalized_table = str(table_name) if table_name else None
        operation_descriptions.append(
            _describe_leaf_operation(operation, normalized_table)
        )
        if not table_name:
            unknown_operations.append(type(operation).__name__)

    for operation in operations:
        visit(operation)

    return DriftInspection(
        tables=frozenset(tables),
        unknown_operations=tuple(unknown_operations),
        operation_descriptions=tuple(operation_descriptions),
    )


def inspect_database_drift() -> DriftInspection:
    """Executa autogenerate contra o banco configurado e classifica deriva."""

    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.connect() as connection:
            migration_context = MigrationContext.configure(connection)
            migration_script = produce_migrations(
                migration_context, Base.metadata
            )
            upgrade_ops = migration_script.upgrade_ops
            if upgrade_ops is None:
                return DriftInspection(
                    tables=frozenset(),
                    unknown_operations=("MissingUpgradeOps",),
                )
            return inspect_upgrade_operations(upgrade_ops.ops)
    finally:
        engine.dispose()


def main() -> int:
    inspection = inspect_database_drift()

    if not inspection.has_drift:
        print("Alembic metadata drift gate: no drift detected.")
        return 0

    tables = ", ".join(sorted(inspection.tables)) or "<none>"
    if inspection.is_allowed:
        print(
            "Alembic metadata drift gate: accepted temporary drift in "
            f"{tables}."
        )
        return 0

    print(f"Alembic metadata drift gate: BLOCKED; drift tables: {tables}.")
    if inspection.operation_descriptions:
        print("Autogenerate operations:")
        for description in inspection.operation_descriptions:
            print(f"- {description}")
    if inspection.unknown_operations:
        print(
            "Unclassified autogenerate operations: "
            + ", ".join(inspection.unknown_operations)
        )
    print("Zero schema drift is permitted.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
