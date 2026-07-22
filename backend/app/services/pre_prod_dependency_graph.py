"""Grafo dirigido reutilizável para dependências entre tabelas.

A aresta ``dependent -> dependency`` significa que a tabela de origem depende da
tabela de destino. O módulo é puro: não acessa banco, não executa SQL e não
conhece políticas de limpeza.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableDependency:
    dependent: str
    dependency: str
    constraint_name: str | None = None

    def __post_init__(self) -> None:
        if not self.dependent.strip() or not self.dependency.strip():
            raise ValueError("dependency table names cannot be empty")


@dataclass(frozen=True)
class DependencyPlan:
    rebuild_order: list[str]
    cleanup_order: list[str]
    cycles: list[list[str]]

    @property
    def ok(self) -> bool:
        return not self.cycles


class TableDependencyGraph:
    """DAG determinístico com detecção de ciclos e ordenação topológica."""

    def __init__(
        self,
        *,
        tables: list[str],
        dependencies: list[TableDependency],
    ) -> None:
        normalized_tables = sorted(set(tables))
        if any(not table.strip() for table in normalized_tables):
            raise ValueError("table names cannot be empty")

        known_tables = set(normalized_tables)
        for edge in dependencies:
            if edge.dependent not in known_tables or edge.dependency not in known_tables:
                raise ValueError(
                    "dependency references unknown table: "
                    f"{edge.dependent!r} -> {edge.dependency!r}"
                )

        self._tables = normalized_tables
        self._dependencies = sorted(
            set(dependencies),
            key=lambda edge: (
                edge.dependent,
                edge.dependency,
                edge.constraint_name or "",
            ),
        )

    @property
    def tables(self) -> list[str]:
        return list(self._tables)

    @property
    def dependencies(self) -> list[TableDependency]:
        return list(self._dependencies)

    def direct_dependencies(self, table: str) -> list[str]:
        self._require_table(table)
        return sorted(
            {
                edge.dependency
                for edge in self._dependencies
                if edge.dependent == table
            }
        )

    def direct_dependents(self, table: str) -> list[str]:
        self._require_table(table)
        return sorted(
            {
                edge.dependent
                for edge in self._dependencies
                if edge.dependency == table
            }
        )

    def build_plan(self) -> DependencyPlan:
        cycles = self._find_cycles()
        if cycles:
            return DependencyPlan(rebuild_order=[], cleanup_order=[], cycles=cycles)

        rebuild_order = self._topological_order()
        return DependencyPlan(
            rebuild_order=rebuild_order,
            cleanup_order=list(reversed(rebuild_order)),
            cycles=[],
        )

    def _topological_order(self) -> list[str]:
        dependency_count = {table: 0 for table in self._tables}
        dependents: dict[str, set[str]] = {table: set() for table in self._tables}

        for dependent, dependency in {
            (edge.dependent, edge.dependency) for edge in self._dependencies
        }:
            dependency_count[dependent] += 1
            dependents[dependency].add(dependent)

        ready = sorted(
            table for table, count in dependency_count.items() if count == 0
        )
        ordered: list[str] = []

        while ready:
            current = ready.pop(0)
            ordered.append(current)
            for dependent in sorted(dependents[current]):
                dependency_count[dependent] -= 1
                if dependency_count[dependent] == 0:
                    ready.append(dependent)
                    ready.sort()

        if len(ordered) != len(self._tables):
            raise RuntimeError("topological ordering requested for cyclic graph")
        return ordered

    def _find_cycles(self) -> list[list[str]]:
        adjacency = {
            table: self.direct_dependencies(table)
            for table in self._tables
        }
        state: dict[str, int] = {table: 0 for table in self._tables}
        stack: list[str] = []
        cycles: set[tuple[str, ...]] = set()

        def visit(table: str) -> None:
            state[table] = 1
            stack.append(table)
            for dependency in adjacency[table]:
                if state[dependency] == 0:
                    visit(dependency)
                elif state[dependency] == 1:
                    start = stack.index(dependency)
                    cycle = stack[start:] + [dependency]
                    cycles.add(self._normalize_cycle(cycle))
            stack.pop()
            state[table] = 2

        for table in self._tables:
            if state[table] == 0:
                visit(table)

        return [list(cycle) for cycle in sorted(cycles)]

    @staticmethod
    def _normalize_cycle(cycle: list[str]) -> tuple[str, ...]:
        nodes = cycle[:-1]
        rotations = [nodes[index:] + nodes[:index] for index in range(len(nodes))]
        normalized = min(rotations)
        return tuple(normalized + [normalized[0]])

    def _require_table(self, table: str) -> None:
        if table not in self._tables:
            raise ValueError(f"unknown table: {table!r}")
