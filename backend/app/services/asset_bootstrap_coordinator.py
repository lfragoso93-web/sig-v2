"""Orquestrador neutro do bootstrap canônico de ativos."""

from __future__ import annotations

from collections.abc import Sequence

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapCapability,
    AssetBootstrapCapabilityName,
    AssetBootstrapCapabilityResult,
    AssetBootstrapCoverageSummary,
    AssetBootstrapReport,
    AssetBootstrapRequest,
)
from app.services.asset_bootstrap_dependency_policy import (
    AssetBootstrapDependencyPolicy,
    DEFAULT_ASSET_BOOTSTRAP_DEPENDENCY_POLICY,
)


class AssetBootstrapCoordinator:
    """Executa capacidades independentes em ordem explícita e auditável."""

    def __init__(
        self,
        capabilities: Sequence[AssetBootstrapCapability],
        *,
        dependency_policy: AssetBootstrapDependencyPolicy = (
            DEFAULT_ASSET_BOOTSTRAP_DEPENDENCY_POLICY
        ),
    ) -> None:
        self._capabilities = tuple(capabilities)
        self._dependency_policy = dependency_policy

    async def execute(self, request: AssetBootstrapRequest) -> AssetBootstrapReport:
        ticker = request.ticker.strip().upper()
        asset_type = request.asset_type.strip().upper()
        if not ticker:
            raise ValueError("ticker is required")
        if not asset_type:
            raise ValueError("asset_type is required")

        normalized_request = AssetBootstrapRequest(
            ticker=ticker,
            asset_type=asset_type,
        )
        results: list[AssetBootstrapCapabilityResult] = []
        completed: dict[AssetBootstrapCapabilityName, AssetBootstrapCapabilityResult] = {}

        for capability in self._capabilities:
            failed_dependencies = tuple(
                dependency
                for dependency in self._dependency_policy.required_for(capability.name)
                if dependency not in completed or not completed[dependency].ok
            )
            if failed_dependencies:
                result = AssetBootstrapCapabilityResult(
                    capability=capability.name,
                    ok=False,
                    errors=(
                        "blocked_by_dependency:"
                        + ",".join(item.value for item in failed_dependencies),
                    ),
                )
            else:
                result = await capability.execute(normalized_request)
                if result.capability is not capability.name:
                    raise ValueError(
                        "capability result name does not match registered capability"
                    )

            results.append(result)
            completed[result.capability] = result

        coverage = AssetBootstrapCoverageSummary(
            total_capabilities=len(results),
            successful_capabilities=sum(result.ok for result in results),
            failed_capabilities=tuple(
                result.capability.value for result in results if not result.ok
            ),
            created=sum(result.created for result in results),
            updated=sum(result.updated for result in results),
            unchanged=sum(result.unchanged for result in results),
            warnings=sum(len(result.warnings) for result in results),
            errors=sum(len(result.errors) for result in results),
        )

        return AssetBootstrapReport(
            ticker=ticker,
            asset_type=asset_type,
            ok=not coverage.failed_capabilities,
            capabilities=tuple(results),
            coverage=coverage,
        )
