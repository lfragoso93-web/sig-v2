from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import pre_prod_cleanup_impact_service as service


class FakeSession:
    def __init__(self) -> None:
        self.rollback_calls = 0
        self.close_calls = 0

    async def rollback(self) -> None:
        self.rollback_calls += 1

    async def close(self) -> None:
        self.close_calls += 1


def _inventory():  # type: ignore[no-untyped-def]
    return SimpleNamespace(
        schema_version="pre-prod-inventory.v2",
        generated_at="2026-07-22T15:00:00+00:00",
        tables=[
            SimpleNamespace(
                name="transactions",
                classification="export_before_cleanup",
                rationale="user data",
                row_count=1,
            )
        ],
    )


@pytest.mark.asyncio
async def test_supplied_session_can_preserve_shared_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()

    async def fake_inventory(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return _inventory()

    async def fake_dependencies(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return []

    class FakeGraph:
        def __init__(self, **_kwargs):  # type: ignore[no-untyped-def]
            pass

        def build_plan(self):  # type: ignore[no-untyped-def]
            return SimpleNamespace(
                cleanup_order=["transactions"],
                rebuild_order=[],
                cycles=[],
            )

    monkeypatch.setattr(service, "build_pre_prod_inventory", fake_inventory)
    monkeypatch.setattr(service, "discover_table_dependencies", fake_dependencies)
    monkeypatch.setattr(service, "TableDependencyGraph", FakeGraph)

    report = await service.build_pre_prod_cleanup_impact(
        branch="stable-15jun",
        commit_sha="a" * 40,
        session=session,  # type: ignore[arg-type]
        rollback_supplied_session=False,
    )

    assert report.ok is True
    assert report.dependency_plan.export_required_before_cleanup == ["transactions"]
    assert session.rollback_calls == 0
    assert session.close_calls == 0
