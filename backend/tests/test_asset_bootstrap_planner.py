from __future__ import annotations

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapRequest,
    AssetBootstrapStageState,
)
from app.services.asset_bootstrap_planner import plan_asset_bootstrap
from tests.fixtures.asset_bootstrap_capabilities import (
    catalog_fixture_capability,
    corporate_events_fixture_capability,
    coverage_fixture_capability,
    income_events_fixture_capability,
    quotes_fixture_capability,
)


def _capabilities():
    return (
        catalog_fixture_capability(),
        quotes_fixture_capability(),
        income_events_fixture_capability(),
        corporate_events_fixture_capability(),
        coverage_fixture_capability(),
    )


def test_planner_marks_every_stage_as_planned_without_execution() -> None:
    capabilities = _capabilities()

    report = plan_asset_bootstrap(
        capabilities,
        AssetBootstrapRequest(ticker=" petr4 ", asset_type=" acao "),
    )

    assert report.ticker == "PETR4"
    assert report.asset_type == "ACAO"
    assert report.ok is False
    assert [item.state for item in report.capabilities] == [
        AssetBootstrapStageState.PLANNED,
    ] * 5
    assert all(not capability.requests for capability in capabilities)
    assert report.coverage.total_capabilities == 5
    assert report.coverage.successful_capabilities == 0
    assert report.coverage.failed_capabilities == ()
    assert report.coverage.blocked_capabilities == ()


def test_planner_rejects_invalid_identity_before_returning_plan() -> None:
    capabilities = _capabilities()

    try:
        plan_asset_bootstrap(
            capabilities,
            AssetBootstrapRequest(ticker=" ", asset_type="ACAO"),
        )
    except ValueError as exc:
        assert str(exc) == "ticker is required"
    else:
        raise AssertionError("expected ValueError")

    assert all(not capability.requests for capability in capabilities)
