"""Validação estrutural da configuração do bootstrap canônico de ativos."""

from __future__ import annotations

from collections.abc import Sequence

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapCapability,
    AssetBootstrapCapabilityName,
)
from app.services.asset_bootstrap_dependency_policy import (
    AssetBootstrapDependencyPolicy,
    DEFAULT_ASSET_BOOTSTRAP_DEPENDENCY_POLICY,
)


def validate_asset_bootstrap_configuration(
    capabilities: Sequence[AssetBootstrapCapability],
    *,
    dependency_policy: AssetBootstrapDependencyPolicy = (
        DEFAULT_ASSET_BOOTSTRAP_DEPENDENCY_POLICY
    ),
) -> None:
    """Rejeita duplicidade, ciclos e dependência posterior antes da execução."""

    names = [capability.name for capability in capabilities]
    duplicates = sorted(
        {name.value for name in names if names.count(name) > 1}
    )
    if duplicates:
        raise ValueError(
            "duplicate capabilities: " + ",".join(duplicates)
        )

    visiting: set[AssetBootstrapCapabilityName] = set()
    visited: set[AssetBootstrapCapabilityName] = set()

    def visit(name: AssetBootstrapCapabilityName) -> None:
        if name in visiting:
            raise ValueError(f"cyclic capability dependency: {name.value}")
        if name in visited:
            return
        visiting.add(name)
        for dependency in dependency_policy.required_for(name):
            visit(dependency)
        visiting.remove(name)
        visited.add(name)

    for name in AssetBootstrapCapabilityName:
        visit(name)

    positions = {name: index for index, name in enumerate(names)}
    for name in names:
        for dependency in dependency_policy.required_for(name):
            if dependency not in positions:
                continue
            if positions[dependency] >= positions[name]:
                raise ValueError(
                    f"invalid capability order: {dependency.value} must precede "
                    f"{name.value}"
                )
