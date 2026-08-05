"""Planejamento neutro do bootstrap canônico de ativos."""

from __future__ import annotations

from collections.abc import Sequence

from app.services.asset_bootstrap_configuration_validator import (
    validate_asset_bootstrap_configuration,
)
from app.services.asset_bootstrap_contracts import (
    AssetBootstrapCapability,
    AssetBootstrapCapabilityResult,
    AssetBootstrapCoverageSummary,
    AssetBootstrapExecutionIdentity,
    AssetBootstrapReport,
    AssetBootstrapRequest,
    AssetBootstrapStageState,
)
from app.services.asset_bootstrap_dependency_policy import (
    AssetBootstrapDependencyPolicy,
    DEFAULT_ASSET_BOOTSTRAP_DEPENDENCY_POLICY,
)


def plan_asset_bootstrap(
    capabilities: Sequence[AssetBootstrapCapability],
    request: AssetBootstrapRequest,
    *,
    identity: AssetBootstrapExecutionIdentity | None = None,
    dependency_policy: AssetBootstrapDependencyPolicy = (
        DEFAULT_ASSET_BOOTSTRAP_DEPENDENCY_POLICY
    ),
) -> AssetBootstrapReport:
    """Retorna todas as etapas planejadas sem executar nenhuma capacidade."""

    validate_asset_bootstrap_configuration(
        capabilities,
        dependency_policy=dependency_policy,
    )
    ticker = request.ticker.strip().upper()
    asset_type = request.asset_type.strip().upper()
    if not ticker:
        raise ValueError("ticker is required")
    if not asset_type:
        raise ValueError("asset_type is required")

    results = tuple(
        AssetBootstrapCapabilityResult(
            capability=capability.name,
            ok=False,
            state=AssetBootstrapStageState.PLANNED,
        )
        for capability in capabilities
    )
    coverage = AssetBootstrapCoverageSummary(
        total_capabilities=len(results),
        successful_capabilities=0,
        failed_capabilities=(),
        blocked_capabilities=(),
        created=0,
        updated=0,
        unchanged=0,
        warnings=0,
        errors=0,
    )
    return AssetBootstrapReport(
        ticker=ticker,
        asset_type=asset_type,
        ok=False,
        capabilities=results,
        coverage=coverage,
        identity=identity.normalized() if identity is not None else None,
    )
