from __future__ import annotations

import pytest

from app.services.asset_bootstrap_report_diff_service import (
    compare_asset_bootstrap_reports,
)


def _report(*, state: str = "executed", warnings=None, errors=None, created=1):
    return {
        "ticker": "PETR4",
        "asset_type": "ACAO",
        "ok": not errors,
        "coverage": {
            "total_capabilities": 1,
            "successful_capabilities": 0 if errors else 1,
            "failed_capabilities": ["catalog"] if errors else [],
            "blocked_capabilities": [],
            "created": created,
            "updated": 0,
            "unchanged": 0,
            "warnings": len(warnings or []),
            "errors": len(errors or []),
        },
        "capabilities": [
            {
                "capability": "catalog",
                "ok": not errors,
                "state": state,
                "created": created,
                "updated": 0,
                "unchanged": 0,
                "warnings": warnings or [],
                "errors": errors or [],
            }
        ],
    }


def test_equivalent_reports_have_no_changes() -> None:
    report = _report()

    diff = compare_asset_bootstrap_reports(report, dict(report))

    assert diff.equivalent is True
    assert diff.changed_fields == ()
    assert diff.changed_capabilities == ()


def test_detects_state_count_warning_and_error_changes() -> None:
    before = _report()
    after = _report(
        state="failed",
        warnings=["partial_coverage"],
        errors=["provider_unavailable"],
        created=0,
    )

    diff = compare_asset_bootstrap_reports(before, after)

    assert diff.equivalent is False
    assert "ok" in diff.changed_fields
    assert "coverage" in diff.changed_fields
    assert diff.changed_capabilities == ("catalog",)


def test_rejects_duplicate_capabilities() -> None:
    report = _report()
    report["capabilities"] = report["capabilities"] * 2

    with pytest.raises(ValueError, match="duplicate capability: catalog"):
        compare_asset_bootstrap_reports(report, _report())
