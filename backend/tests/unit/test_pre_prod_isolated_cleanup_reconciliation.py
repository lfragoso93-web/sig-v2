from pathlib import Path

import pytest

from app.services.pre_prod_isolated_cleanup_reconciliation import (
    IsolatedCleanupReconciliationError,
    publish,
    reconcile,
)


def _snapshot(users: int, transactions: int) -> dict[str, object]:
    return {
        "generated_at": "2026-07-23T00:00:00+00:00",
        "tables": [
            {"name": "users", "classification": "preserved", "row_count": users},
            {
                "name": "transactions",
                "classification": "export_before_cleanup",
                "row_count": transactions,
            },
        ],
    }


def test_reconciliation_accepts_committed_cleanup_and_preserved_baseline() -> None:
    result = reconcile(
        _snapshot(2, 3),
        _snapshot(2, 0),
        ("transactions",),
        committed=True,
    )
    assert result["ok"] is True
    assert result["preserved_tables_unchanged"] is True


def test_reconciliation_accepts_complete_rollback() -> None:
    result = reconcile(
        _snapshot(2, 3),
        _snapshot(2, 3),
        ("transactions",),
        committed=False,
    )
    assert result["ok"] is True


def test_reconciliation_rejects_change_outside_cleanup_order() -> None:
    result = reconcile(
        _snapshot(2, 3),
        _snapshot(1, 0),
        ("transactions",),
        committed=True,
    )
    assert result["ok"] is False
    assert result["preserved_tables_unchanged"] is False


def test_atomic_evidence_refuses_overwrite(tmp_path: Path) -> None:
    destination = tmp_path / "reconciliation.json"
    publish(destination, {"ok": True})
    with pytest.raises(IsolatedCleanupReconciliationError, match="already exists"):
        publish(destination, {"ok": False})
