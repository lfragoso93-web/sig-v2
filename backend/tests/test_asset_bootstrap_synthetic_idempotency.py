from __future__ import annotations

import pytest

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapExecutionIdentity,
    AssetBootstrapRequest,
)
from app.services.asset_bootstrap_coordinator import AssetBootstrapCoordinator
from tests.fixtures.asset_bootstrap_capabilities import (
    catalog_fixture_capability,
    corporate_events_fixture_capability,
    coverage_fixture_capability,
    income_events_fixture_capability,
    quotes_fixture_capability,
)


def _capabilities():
    return (
        catalog_fixture_capability(unchanged=1, created=0),
        quotes_fixture_capability(unchanged=1),
        income_events_fixture_capability(unchanged=1),
        corporate_events_fixture_capability(unchanged=1),
        coverage_fixture_capability(unchanged=1),
    )


@pytest.mark.asyncio
async def test_repeated_simulated_execution_is_deterministic() -> None:
    request = AssetBootstrapRequest(ticker="petr4", asset_type="acao")
    identity = AssetBootstrapExecutionIdentity(
        run_id="synthetic-idempotency",
        branch="stable-15jun",
        commit_sha="abcdef1234567890",
    )

    first = await AssetBootstrapCoordinator(_capabilities()).execute(
        request,
        identity=identity,
    )
    second = await AssetBootstrapCoordinator(_capabilities()).execute(
        request,
        identity=identity,
    )

    assert first.to_dict() == second.to_dict()
    assert first.ok is True
    assert first.coverage.created == 0
    assert first.coverage.updated == 0
    assert first.coverage.unchanged == 5


@pytest.mark.asyncio
async def test_run_identity_change_does_not_change_financial_counts() -> None:
    request = AssetBootstrapRequest(ticker="petr4", asset_type="acao")

    first = await AssetBootstrapCoordinator(_capabilities()).execute(
        request,
        identity=AssetBootstrapExecutionIdentity(
            run_id="run-1",
            branch="stable-15jun",
            commit_sha="abcdef1234567890",
        ),
    )
    second = await AssetBootstrapCoordinator(_capabilities()).execute(
        request,
        identity=AssetBootstrapExecutionIdentity(
            run_id="run-2",
            branch="stable-15jun",
            commit_sha="abcdef1234567890",
        ),
    )

    assert first.identity != second.identity
    assert first.capabilities == second.capabilities
    assert first.coverage == second.coverage
