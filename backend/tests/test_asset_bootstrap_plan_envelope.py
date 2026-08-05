"""Caracteriza identidade auditável e envelope read-only do planejamento."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapCapabilityName,
    AssetBootstrapCapabilityResult,
    AssetBootstrapExecutionIdentity,
    AssetBootstrapRequest,
)
from app.services.asset_bootstrap_plan_envelope import AssetBootstrapPlanEnvelope
from app.services.asset_bootstrap_planner import plan_asset_bootstrap


@dataclass(frozen=True)
class _NeverExecuteCapability:
    name: AssetBootstrapCapabilityName

    async def execute(
        self,
        request: AssetBootstrapRequest,
    ) -> AssetBootstrapCapabilityResult:
        raise AssertionError("planning must not execute capabilities")


def _capabilities() -> tuple[_NeverExecuteCapability, ...]:
    return tuple(
        _NeverExecuteCapability(name)
        for name in (
            AssetBootstrapCapabilityName.CATALOG,
            AssetBootstrapCapabilityName.QUOTES,
            AssetBootstrapCapabilityName.INCOME_EVENTS,
            AssetBootstrapCapabilityName.CORPORATE_EVENTS,
            AssetBootstrapCapabilityName.COVERAGE,
        )
    )


def test_plan_envelope_is_versioned_auditable_and_read_only() -> None:
    report = plan_asset_bootstrap(
        _capabilities(),
        AssetBootstrapRequest(ticker=" petr4 ", asset_type=" acao "),
        identity=AssetBootstrapExecutionIdentity(
            run_id=" run-001 ",
            branch=" stable-15jun ",
            commit_sha=" ABCDEF123 ",
        ),
    )

    payload = AssetBootstrapPlanEnvelope(report).to_dict()

    assert payload["schema_version"] == "asset-bootstrap-plan.v1"
    assert payload["mode"] == "plan"
    assert payload["dry_run"] is True
    assert payload["read_only"] is True
    assert payload["writes_executed"] is False
    assert payload["report"]["identity"] == {
        "run_id": "run-001",
        "branch": "stable-15jun",
        "commit_sha": "abcdef123",
    }
    assert payload["report"]["ticker"] == "PETR4"
    assert payload["report"]["asset_type"] == "ACAO"
    assert {
        item["state"] for item in payload["report"]["capabilities"]
    } == {"planned"}


@pytest.mark.parametrize(
    ("identity", "message"),
    [
        (AssetBootstrapExecutionIdentity("", "stable-15jun", "abc"), "run_id"),
        (AssetBootstrapExecutionIdentity("run", "", "abc"), "branch"),
        (AssetBootstrapExecutionIdentity("run", "stable-15jun", ""), "commit_sha"),
    ],
)
def test_invalid_identity_is_rejected(
    identity: AssetBootstrapExecutionIdentity,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        plan_asset_bootstrap(
            _capabilities(),
            AssetBootstrapRequest(ticker="PETR4", asset_type="ACAO"),
            identity=identity,
        )
