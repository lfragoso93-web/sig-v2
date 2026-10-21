from __future__ import annotations

from dataclasses import dataclass, field

from app.governance.alembic_drift_gate import (
    ALLOWED_DRIFT_TABLES,
    inspect_upgrade_operations,
)


@dataclass
class _Operation:
    table_name: str | None = None
    ops: list[object] = field(default_factory=list)


class _UnknownOperation:
    pass


def test_allowed_drift_is_empty() -> None:
    assert ALLOWED_DRIFT_TABLES == frozenset()


def test_no_operations_means_no_drift() -> None:
    inspection = inspect_upgrade_operations(())

    assert inspection.has_drift is False
    assert inspection.is_allowed is False
    assert inspection.tables == frozenset()
    assert inspection.unknown_operations == ()


def test_table_drift_is_not_allowed_when_whitelist_empty() -> None:
    inspection = inspect_upgrade_operations(
        (
            _Operation(
                table_name="goals",
                ops=[_Operation(), _Operation()],
            ),
        )
    )

    assert inspection.has_drift is True
    assert inspection.is_allowed is False
    assert inspection.tables == frozenset({"goals"})
    assert inspection.unknown_operations == ()


def test_any_table_drift_blocks() -> None:
    inspection = inspect_upgrade_operations(
        (
            _Operation(table_name="goals", ops=[_Operation()]),
            _Operation(table_name="assets", ops=[_Operation()]),
        )
    )

    assert inspection.has_drift is True
    assert inspection.is_allowed is False
    assert inspection.tables == frozenset({"assets", "goals"})


def test_unclassified_leaf_operation_fails_closed() -> None:
    inspection = inspect_upgrade_operations((_UnknownOperation(),))

    assert inspection.has_drift is True
    assert inspection.is_allowed is False
    assert inspection.tables == frozenset()
    assert inspection.unknown_operations == ("_UnknownOperation",)
