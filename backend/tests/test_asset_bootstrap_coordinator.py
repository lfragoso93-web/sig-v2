"""Caracteriza a fundação neutra do bootstrap canônico de ativos."""

from dataclasses import dataclass

import pytest

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapCapabilityName,
    AssetBootstrapCapabilityResult,
    AssetBootstrapRequest,
)
from app.services.asset_bootstrap_coordinator import AssetBootstrapCoordinator


@dataclass
class _Capability:
    name: AssetBootstrapCapabilityName
    ok: bool = True

    async def execute(
        self,
        request: AssetBootstrapRequest,
    ) -> AssetBootstrapCapabilityResult:
        assert request.ticker == "ABCD3"
        assert request.asset_type == "ACAO"
        return AssetBootstrapCapabilityResult(
            capability=self.name,
            ok=self.ok,
            unchanged=1,
        )


@pytest.mark.asyncio
async def test_coordinator_normalizes_and_preserves_capability_order() -> None:
    coordinator = AssetBootstrapCoordinator(
        [
            _Capability(AssetBootstrapCapabilityName.CATALOG),
            _Capability(AssetBootstrapCapabilityName.QUOTES),
            _Capability(AssetBootstrapCapabilityName.INCOME_EVENTS),
            _Capability(AssetBootstrapCapabilityName.CORPORATE_EVENTS),
            _Capability(AssetBootstrapCapabilityName.COVERAGE),
        ]
    )

    result = await coordinator.execute(
        AssetBootstrapRequest(ticker=" abcd3 ", asset_type=" acao ")
    )

    assert result.ok is True
    assert result.ticker == "ABCD3"
    assert [item.capability.value for item in result.capabilities] == [
        "catalog",
        "quotes",
        "income_events",
        "corporate_events",
        "coverage",
    ]


@pytest.mark.asyncio
async def test_coordinator_reports_partial_failure_without_hiding_results() -> None:
    coordinator = AssetBootstrapCoordinator(
        [
            _Capability(AssetBootstrapCapabilityName.CATALOG),
            _Capability(AssetBootstrapCapabilityName.QUOTES, ok=False),
        ]
    )

    result = await coordinator.execute(
        AssetBootstrapRequest(ticker="ABCD3", asset_type="ACAO")
    )

    assert result.ok is False
    assert len(result.capabilities) == 2
    assert result.capabilities[1].ok is False


@pytest.mark.asyncio
async def test_coordinator_rejects_empty_identity() -> None:
    coordinator = AssetBootstrapCoordinator([])

    with pytest.raises(ValueError, match="ticker is required"):
        await coordinator.execute(
            AssetBootstrapRequest(ticker=" ", asset_type="ACAO")
        )
