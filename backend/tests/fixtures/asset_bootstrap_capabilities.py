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


def _fixture_capability(
    name: AssetBootstrapCapabilityName,
    *,
    created: int = 0,
    updated: int = 0,
    unchanged: int = 0,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> FixtureAssetBootstrapCapability:
    return FixtureAssetBootstrapCapability(
        name=name,
        result=AssetBootstrapCapabilityResult(
            capability=name,
            ok=not errors,
            created=created,
            updated=updated,
            unchanged=unchanged,
            warnings=warnings,
            errors=errors,
        ),
    )


def catalog_fixture_capability(
    *,
    created: int = 1,
    updated: int = 0,
    unchanged: int = 0,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> FixtureAssetBootstrapCapability:
    return _fixture_capability(
        AssetBootstrapCapabilityName.CATALOG,
        created=created,
        updated=updated,
        unchanged=unchanged,
        warnings=warnings,
        errors=errors,
    )


def quotes_fixture_capability(
    *,
    created: int = 0,
    updated: int = 0,
    unchanged: int = 1,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> FixtureAssetBootstrapCapability:
    return _fixture_capability(
        AssetBootstrapCapabilityName.QUOTES,
        created=created,
        updated=updated,
        unchanged=unchanged,
        warnings=warnings,
        errors=errors,
    )


def income_events_fixture_capability(
    *,
    created: int = 0,
    updated: int = 0,
    unchanged: int = 1,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> FixtureAssetBootstrapCapability:
    return _fixture_capability(
        AssetBootstrapCapabilityName.INCOME_EVENTS,
        created=created,
        updated=updated,
        unchanged=unchanged,
        warnings=warnings,
        errors=errors,
    )


def corporate_events_fixture_capability(
    *,
    created: int = 0,
    updated: int = 0,
    unchanged: int = 1,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> FixtureAssetBootstrapCapability:
    return _fixture_capability(
        AssetBootstrapCapabilityName.CORPORATE_EVENTS,
        created=created,
        updated=updated,
        unchanged=unchanged,
        warnings=warnings,
        errors=errors,
    )


def coverage_fixture_capability(
    *,
    created: int = 0,
    updated: int = 0,
    unchanged: int = 0,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> FixtureAssetBootstrapCapability:
    return _fixture_capability(
        AssetBootstrapCapabilityName.COVERAGE,
        created=created,
        updated=updated,
        unchanged=unchanged,
        warnings=warnings,
        errors=errors,
    )
