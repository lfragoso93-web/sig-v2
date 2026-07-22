from __future__ import annotations

import pytest

from app.services.pre_prod_dependency_graph import (
    TableDependency,
    TableDependencyGraph,
)


def test_dependency_plan_builds_rebuild_and_cleanup_orders() -> None:
    graph = TableDependencyGraph(
        tables=["assets", "asset_prices", "portfolio_positions", "snapshots"],
        dependencies=[
            TableDependency("asset_prices", "assets", "fk_prices_assets"),
            TableDependency("portfolio_positions", "assets", "fk_positions_assets"),
            TableDependency("snapshots", "portfolio_positions", "fk_snapshots_positions"),
        ],
    )

    plan = graph.build_plan()

    assert plan.ok is True
    assert plan.cycles == []
    assert plan.rebuild_order == [
        "assets",
        "asset_prices",
        "portfolio_positions",
        "snapshots",
    ]
    assert plan.cleanup_order == [
        "snapshots",
        "portfolio_positions",
        "asset_prices",
        "assets",
    ]


def test_independent_tables_are_ordered_deterministically() -> None:
    graph = TableDependencyGraph(
        tables=["users", "assets", "settings"],
        dependencies=[],
    )

    plan = graph.build_plan()

    assert plan.rebuild_order == ["assets", "settings", "users"]
    assert plan.cleanup_order == ["users", "settings", "assets"]


def test_direct_dependencies_and_dependents_are_exposed() -> None:
    graph = TableDependencyGraph(
        tables=["assets", "asset_prices", "transactions"],
        dependencies=[
            TableDependency("asset_prices", "assets"),
            TableDependency("transactions", "assets"),
        ],
    )

    assert graph.direct_dependencies("transactions") == ["assets"]
    assert graph.direct_dependents("assets") == ["asset_prices", "transactions"]


def test_cycle_blocks_both_orders() -> None:
    graph = TableDependencyGraph(
        tables=["a", "b", "c"],
        dependencies=[
            TableDependency("a", "b"),
            TableDependency("b", "c"),
            TableDependency("c", "a"),
        ],
    )

    plan = graph.build_plan()

    assert plan.ok is False
    assert plan.rebuild_order == []
    assert plan.cleanup_order == []
    assert plan.cycles == [["a", "b", "c", "a"]]


def test_duplicate_edges_do_not_change_plan() -> None:
    edge = TableDependency("asset_prices", "assets", "fk_prices_assets")
    graph = TableDependencyGraph(
        tables=["assets", "asset_prices"],
        dependencies=[edge, edge],
    )

    assert graph.dependencies == [edge]
    assert graph.build_plan().rebuild_order == ["assets", "asset_prices"]


def test_unknown_table_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown table"):
        TableDependencyGraph(
            tables=["assets"],
            dependencies=[TableDependency("asset_prices", "assets")],
        )


def test_self_reference_is_rejected() -> None:
    with pytest.raises(ValueError, match="self-referential"):
        TableDependency("assets", "assets")


def test_lookup_for_unknown_table_is_rejected() -> None:
    graph = TableDependencyGraph(tables=["assets"], dependencies=[])

    with pytest.raises(ValueError, match="unknown table"):
        graph.direct_dependencies("missing")
