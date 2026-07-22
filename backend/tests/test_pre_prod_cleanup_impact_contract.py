from __future__ import annotations

from dataclasses import replace

import pytest

from app.services.pre_prod_cleanup_impact_contract import (
    IMPACT_REPORT_MODE,
    IMPACT_REPORT_SCHEMA_VERSION,
    CleanupImpactDependency,
    CleanupImpactDependencyPlan,
    CleanupImpactSafety,
    CleanupImpactTable,
    CleanupImpactTotals,
    PreProdCleanupImpactReport,
)
from app.services.pre_prod_inventory_service import TableInventory


def _inventory_table(
    name: str,
    classification: str,
    row_count: int = 1,
) -> TableInventory:
    return TableInventory(
        name=name,
        classification=classification,
        rationale=f"policy for {name}",
        row_count=row_count,
    )


def _report(tables: list[CleanupImpactTable]) -> PreProdCleanupImpactReport:
    export_required = sorted(
        table.name for table in tables if table.proposed_action == "export_required"
    )
    rebuildable = sorted(
        table.name for table in tables if table.proposed_action == "clean_and_rebuild"
    )
    blockers = [table.name for table in tables if table.blocked]
    return PreProdCleanupImpactReport(
        schema_version=IMPACT_REPORT_SCHEMA_VERSION,
        generated_at="2026-07-21T12:00:00+00:00",
        mode=IMPACT_REPORT_MODE,
        branch="stable-15jun",
        commit_sha="a" * 40,
        inventory_schema_version="pre-prod-inventory.v2",
        tables=tables,
        totals=CleanupImpactTotals.from_tables(tables),
        dependency_plan=CleanupImpactDependencyPlan(
            dependencies=[],
            cleanup_order=list(reversed(export_required + rebuildable)),
            rebuild_order=rebuildable,
            export_required_before_cleanup=export_required,
            cycles=[],
        ),
        blockers=blockers,
        safety=CleanupImpactSafety(),
    )


@pytest.mark.parametrize(
    ("classification", "expected_action", "expected_blocked"),
    [
        ("preserved", "preserve", False),
        ("export_before_cleanup", "export_required", False),
        ("rebuildable", "clean_and_rebuild", False),
        ("unclassified", "block", True),
    ],
)
def test_inventory_classification_maps_to_proposed_action(
    classification: str,
    expected_action: str,
    expected_blocked: bool,
) -> None:
    impact = CleanupImpactTable.from_inventory(
        _inventory_table("example_table", classification)
    )

    assert impact.proposed_action == expected_action
    assert impact.blocked is expected_blocked


def test_unknown_inventory_classification_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported inventory classification"):
        CleanupImpactTable.from_inventory(
            _inventory_table("example_table", "legacy_cleanup")
        )


def test_negative_row_count_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative row count"):
        CleanupImpactTable.from_inventory(
            _inventory_table("example_table", "preserved", row_count=-1)
        )


def test_totals_are_derived_from_proposed_actions() -> None:
    tables = [
        CleanupImpactTable.from_inventory(
            _inventory_table("users", "preserved", row_count=2)
        ),
        CleanupImpactTable.from_inventory(
            _inventory_table("transactions", "export_before_cleanup", row_count=3)
        ),
        CleanupImpactTable.from_inventory(
            _inventory_table("asset_prices", "rebuildable", row_count=5)
        ),
        CleanupImpactTable.from_inventory(
            _inventory_table("future_table", "unclassified", row_count=7)
        ),
    ]

    assert CleanupImpactTotals.from_tables(tables) == CleanupImpactTotals(
        tables=4,
        rows=17,
        preserved_tables=1,
        export_required_tables=1,
        rebuildable_tables=1,
        blocked_tables=1,
    )


def test_report_is_blocked_when_inventory_contains_unclassified_table() -> None:
    report = _report(
        [
            CleanupImpactTable.from_inventory(
                _inventory_table("users", "preserved")
            ),
            CleanupImpactTable.from_inventory(
                _inventory_table("future_table", "unclassified")
            ),
        ]
    )

    assert report.ok is False
    assert report.blockers == ["future_table"]
    assert report.to_dict()["ok"] is False


def test_report_is_ok_when_all_tables_are_classified() -> None:
    report = _report(
        [
            CleanupImpactTable.from_inventory(
                _inventory_table("users", "preserved")
            ),
            CleanupImpactTable.from_inventory(
                _inventory_table("transactions", "export_before_cleanup")
            ),
            CleanupImpactTable.from_inventory(
                _inventory_table("asset_prices", "rebuildable")
            ),
        ]
    )

    assert report.ok is True
    assert report.dependency_plan.export_required_before_cleanup == ["transactions"]
    assert report.dependency_plan.rebuild_order == ["asset_prices"]
    assert report.safety == CleanupImpactSafety()


def test_preserved_table_cannot_appear_in_cleanup_order() -> None:
    report = _report(
        [
            CleanupImpactTable.from_inventory(
                _inventory_table("users", "preserved")
            ),
            CleanupImpactTable.from_inventory(
                _inventory_table("asset_prices", "rebuildable")
            ),
        ]
    )

    with pytest.raises(ValueError, match="preserved tables"):
        replace(
            report,
            dependency_plan=replace(
                report.dependency_plan,
                cleanup_order=["asset_prices", "users"],
            ),
        )


def test_export_required_table_cannot_bypass_export_gate() -> None:
    report = _report(
        [
            CleanupImpactTable.from_inventory(
                _inventory_table("transactions", "export_before_cleanup")
            )
        ]
    )

    with pytest.raises(ValueError, match="export gate"):
        replace(
            report,
            dependency_plan=replace(
                report.dependency_plan,
                export_required_before_cleanup=[],
            ),
        )


def test_rebuild_order_must_match_exactly_rebuildable_tables() -> None:
    report = _report(
        [
            CleanupImpactTable.from_inventory(
                _inventory_table("asset_prices", "rebuildable")
            )
        ]
    )

    with pytest.raises(ValueError, match="exactly rebuildable"):
        replace(
            report,
            dependency_plan=replace(report.dependency_plan, rebuild_order=[]),
        )


def test_cycle_is_a_formal_blocker() -> None:
    tables = [
        CleanupImpactTable.from_inventory(
            _inventory_table("asset_prices", "rebuildable")
        )
    ]
    report = PreProdCleanupImpactReport(
        schema_version=IMPACT_REPORT_SCHEMA_VERSION,
        generated_at="2026-07-21T12:00:00+00:00",
        mode=IMPACT_REPORT_MODE,
        branch="stable-15jun",
        commit_sha="a" * 40,
        inventory_schema_version="pre-prod-inventory.v2",
        tables=tables,
        totals=CleanupImpactTotals.from_tables(tables),
        dependency_plan=CleanupImpactDependencyPlan(
            dependencies=[
                CleanupImpactDependency("asset_prices", "asset_prices", "fk_self")
            ],
            cleanup_order=["asset_prices"],
            rebuild_order=["asset_prices"],
            export_required_before_cleanup=[],
            cycles=[["asset_prices", "asset_prices"]],
        ),
        blockers=["referential_cycle:asset_prices->asset_prices"],
        safety=CleanupImpactSafety(),
    )

    assert report.ok is False


def test_report_rejects_inconsistent_totals() -> None:
    report = _report(
        [CleanupImpactTable.from_inventory(_inventory_table("users", "preserved"))]
    )

    with pytest.raises(ValueError, match="totals do not match"):
        replace(
            report,
            totals=CleanupImpactTotals(
                tables=0,
                rows=0,
                preserved_tables=0,
                export_required_tables=0,
                rebuildable_tables=0,
                blocked_tables=0,
            ),
        )


@pytest.mark.parametrize(
    "safety",
    [
        {"read_only": False},
        {"writes_executed": 1},
        {"cleanup_executed": True},
        {"rebuild_executed": True},
    ],
)
def test_safety_contract_rejects_side_effects(safety: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        CleanupImpactSafety(**safety)  # type: ignore[arg-type]
