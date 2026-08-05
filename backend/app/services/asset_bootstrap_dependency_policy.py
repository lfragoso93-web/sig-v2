"""Política neutra de dependências do bootstrap canônico de ativos."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.asset_bootstrap_contracts import AssetBootstrapCapabilityName


@dataclass(frozen=True)
class AssetBootstrapDependencyPolicy:
    dependencies: dict[
        AssetBootstrapCapabilityName,
        tuple[AssetBootstrapCapabilityName, ...],
    ]

    def required_for(
        self,
        capability: AssetBootstrapCapabilityName,
    ) -> tuple[AssetBootstrapCapabilityName, ...]:
        return self.dependencies.get(capability, ())


DEFAULT_ASSET_BOOTSTRAP_DEPENDENCY_POLICY = AssetBootstrapDependencyPolicy(
    dependencies={
        AssetBootstrapCapabilityName.QUOTES: (
            AssetBootstrapCapabilityName.CATALOG,
        ),
        AssetBootstrapCapabilityName.INCOME_EVENTS: (
            AssetBootstrapCapabilityName.CATALOG,
        ),
        AssetBootstrapCapabilityName.CORPORATE_EVENTS: (
            AssetBootstrapCapabilityName.CATALOG,
        ),
        AssetBootstrapCapabilityName.COVERAGE: (
            AssetBootstrapCapabilityName.CATALOG,
            AssetBootstrapCapabilityName.QUOTES,
            AssetBootstrapCapabilityName.INCOME_EVENTS,
            AssetBootstrapCapabilityName.CORPORATE_EVENTS,
        ),
    }
)
