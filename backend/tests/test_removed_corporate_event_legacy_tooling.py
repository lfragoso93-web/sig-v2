from pathlib import Path


_BACKEND_ROOT = Path(__file__).resolve().parents[1]


_REMOVED_PATHS = (
    _BACKEND_ROOT / "app/cli/audit_corporate_event_legacy_inventory.py",
    _BACKEND_ROOT / "app/cli/dry_run_corporate_event_legacy_classification.py",
    _BACKEND_ROOT / "app/cli/plan_corporate_event_legacy_backfill.py",
    _BACKEND_ROOT / "app/cli/compare_corporate_event_backfill_plans.py",
    _BACKEND_ROOT / "app/services/corporate_event_legacy_inventory_service.py",
    _BACKEND_ROOT / "app/services/corporate_event_legacy_dry_run_service.py",
    _BACKEND_ROOT / "app/services/corporate_event_legacy_backfill_plan_service.py",
    _BACKEND_ROOT / "app/services/corporate_event_backfill_plan_diff_service.py",
)


def test_corporate_event_legacy_tooling_remains_removed() -> None:
    unexpected = [str(path.relative_to(_BACKEND_ROOT)) for path in _REMOVED_PATHS if path.exists()]
    assert unexpected == [], f"legacy corporate-event tooling voltou ao backend: {unexpected}"
