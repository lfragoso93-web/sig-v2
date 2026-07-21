from __future__ import annotations

from dataclasses import replace

import pytest

from app.services.pre_prod_cleanup_impact_contract import (
    IMPACT_REPORT_MODE,
    IMPACT_REPORT_SCHEMA_VERSION,
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

    totals = CleanupImpactTotals.from_tables(tables)

    assert totals == CleanupImpactTotals(
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
    assert report.blockers == []
    assert report.safety == CleanupImpactSafety()


def test_report_rejects_inconsistent_totals() -> None:
    report = _report(
        [
            CleanupImpactTable.from_inventory(
                _inventory_table("users", "preserved")
            )
        ]
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


def test_report_rejects_blockers_that_do_not_match_tables() -> None:
    report = _report(
        [
            CleanupImpactTable.from_inventory(
                _inventory_table("future_table", "unclassified")
            )
        ]
    )

    with pytest.raises(ValueError, match="blockers must match"):
        replace(report, blockers=[])


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
