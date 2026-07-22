"""Introspecção read-only de foreign keys para o planejamento pré-produção.

O módulo consulta somente metadados do banco e converte cada foreign key para a
representação canônica ``TableDependency``. Nenhuma política de limpeza é
conhecida aqui e nenhum comando de escrita é executado.
"""
from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pre_prod_dependency_graph import TableDependency


_POSTGRES_FOREIGN_KEYS_SQL = """
SELECT
    tc.constraint_name,
    tc.table_name AS dependent_table,
    ccu.table_name AS dependency_table
FROM information_schema.table_constraints AS tc
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_catalog = tc.constraint_catalog
 AND ccu.constraint_schema = tc.constraint_schema
 AND ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
  AND ccu.table_schema = 'public'
ORDER BY tc.table_name, ccu.table_name, tc.constraint_name
"""


def _normalize_tables(tables: Iterable[str]) -> list[str]:
    normalized = sorted(set(tables))
    if any(not table.strip() for table in normalized):
        raise ValueError("table names cannot be empty")
    return normalized


async def discover_table_dependencies(
    session: AsyncSession,
    *,
    tables: Iterable[str],
) -> list[TableDependency]:
    """Descobre foreign keys existentes entre as tabelas informadas.

    Relações que apontam para tabelas fora do inventário são rejeitadas para
    impedir que o plano ignore dependências estruturais relevantes.
    """
    normalized_tables = _normalize_tables(tables)
    known_tables = set(normalized_tables)
    dialect = session.bind.dialect.name if session.bind is not None else "unknown"

    if dialect == "sqlite":
        dependencies = await _discover_sqlite_dependencies(
            session,
            normalized_tables,
        )
    else:
        dependencies = await _discover_postgres_dependencies(session)

    external = sorted(
        {
            edge.dependency
            for edge in dependencies
            if edge.dependent in known_tables and edge.dependency not in known_tables
        }
    )
    if external:
        raise ValueError(
            "foreign keys reference tables outside inventory: " + ", ".join(external)
        )

    return sorted(
        {
            edge
            for edge in dependencies
            if edge.dependent in known_tables and edge.dependency in known_tables
        },
        key=lambda edge: (
            edge.dependent,
            edge.dependency,
            edge.constraint_name or "",
        ),
    )


async def _discover_postgres_dependencies(
    session: AsyncSession,
) -> list[TableDependency]:
    result = await session.execute(text(_POSTGRES_FOREIGN_KEYS_SQL))
    return [
        TableDependency(
            dependent=str(row.dependent_table),
            dependency=str(row.dependency_table),
            constraint_name=str(row.constraint_name),
        )
        for row in result
    ]


async def _discover_sqlite_dependencies(
    session: AsyncSession,
    tables: list[str],
) -> list[TableDependency]:
    dependencies: list[TableDependency] = []
    for table in tables:
        # Nomes vieram do inventário/metadata e são validados antes de interpolar.
        if not table.replace("_", "a").isalnum() or table[0].isdigit():
            raise ValueError(f"unsafe SQLite table name: {table!r}")
        result = await session.execute(text(f'PRAGMA foreign_key_list("{table}")'))
        for row in result:
            dependency = str(row[2])
            constraint_name = f"sqlite_fk_{table}_{int(row[0])}"
            dependencies.append(
                TableDependency(
                    dependent=table,
                    dependency=dependency,
                    constraint_name=constraint_name,
                )
            )
    return dependencies
