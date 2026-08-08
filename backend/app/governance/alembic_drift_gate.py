"""Gate temporário e fail-closed para deriva Alembic ↔ MetaData.

A única exceção arquitetural permitida é ``goals``, conforme Issues #241/#246.
O módulo de Metas permanece bloqueado para redesenho conjunto com #57; este gate
não torna o ORM atual canônico e não substitui uma futura migration do domínio.
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


ALLOWED_DRIFT_TABLES = frozenset({"goals"})


@dataclass(frozen=True)
class DriftInspection:
    tables: frozenset[str]
    unknown_operations: tuple[str, ...]

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


def inspect_upgrade_operations(operations: Iterable[Any]) -> DriftInspection:
    """Classifica operações de autogenerate por tabela, falhando fechado no desconhecido."""

    tables: set[str] = set()
    unknown_operations: list[str] = []

    def visit(operation: Any, inherited_table: str | None = None) -> None:
        table_name = getattr(operation, "table_name", None) or inherited_table
        children = tuple(_operation_children(operation))

        if table_name:
            tables.add(str(table_name))

        if children:
            for child in children:
                visit(child, str(table_name) if table_name else inherited_table)
            return

        if not table_name:
            unknown_operations.append(type(operation).__name__)

    for operation in operations:
        visit(operation)

    return DriftInspection(
        tables=frozenset(tables),
        unknown_operations=tuple(unknown_operations),
    )


def inspect_database_drift() -> DriftInspection:
    """Executa autogenerate contra o banco configurado e classifica a deriva."""

    engine = create_engine(settings.DATABASE_URL)
    try:
        with engine.connect() as connection:
            migration_context = MigrationContext.configure(connection)
            migration_script = produce_migrations(migration_context, Base.metadata)
            return inspect_upgrade_operations(migration_script.upgrade_ops.ops)
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
            "Alembic metadata drift gate: accepted temporary drift only in "
            f"{tables} (tracked by #246/#57)."
        )
        return 0

    print(f"Alembic metadata drift gate: BLOCKED; drift tables: {tables}.")
    if inspection.unknown_operations:
        print(
            "Unclassified autogenerate operations: "
            + ", ".join(inspection.unknown_operations)
        )
    print("Only the explicitly tracked temporary goals drift is allowed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
