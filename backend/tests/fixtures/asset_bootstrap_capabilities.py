"""Capacidades simuladas para caracterizar o bootstrap sem providers ou banco."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapCapabilityName,
    AssetBootstrapCapabilityResult,
    AssetBootstrapRequest,
)


@dataclass
class FixtureAssetBootstrapCapability:
    name: AssetBootstrapCapabilityName
    result: AssetBootstrapCapabilityResult
    requests: list[AssetBootstrapRequest] = field(default_factory=list)

    async def execute(
        self,
        request: AssetBootstrapRequest,
    ) -> AssetBootstrapCapabilityResult:
        self.requests.append(request)
        return self.result


def catalog_fixture_capability(
    *,
    created: int = 1,
    updated: int = 0,
    unchanged: int = 0,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> FixtureAssetBootstrapCapability:
    return FixtureAssetBootstrapCapability(
        name=AssetBootstrapCapabilityName.CATALOG,
        result=AssetBootstrapCapabilityResult(
            capability=AssetBootstrapCapabilityName.CATALOG,
            ok=not errors,
            created=created,
            updated=updated,
            unchanged=unchanged,
            warnings=warnings,
            errors=errors,
        ),
    )
