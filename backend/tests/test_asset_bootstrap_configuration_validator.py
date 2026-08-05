"""Valida a configuração estrutural do bootstrap antes da execução."""

from __future__ import annotations

import pytest

from app.services.asset_bootstrap_configuration_validator import (
    validate_asset_bootstrap_configuration,
)
from app.services.asset_bootstrap_contracts import AssetBootstrapCapabilityName
from app.services.asset_bootstrap_dependency_policy import (
    AssetBootstrapDependencyPolicy,
)
from tests.fixtures.asset_bootstrap_capabilities import (
    catalog_fixture_capability,
    quotes_fixture_capability,
)


def test_duplicate_capabilities_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate capabilities: catalog"):
        validate_asset_bootstrap_configuration(
            [catalog_fixture_capability(), catalog_fixture_capability()]
        )


def test_dependency_must_precede_dependent_capability() -> None:
    with pytest.raises(
        ValueError,
        match="catalog must precede quotes",
    ):
        validate_asset_bootstrap_configuration(
            [quotes_fixture_capability(), catalog_fixture_capability()]
        )


def test_cyclic_dependency_is_rejected() -> None:
    policy = AssetBootstrapDependencyPolicy(
        dependencies={
            AssetBootstrapCapabilityName.CATALOG: (
                AssetBootstrapCapabilityName.QUOTES,
            ),
            AssetBootstrapCapabilityName.QUOTES: (
                AssetBootstrapCapabilityName.CATALOG,
            ),
        }
    )

    with pytest.raises(ValueError, match="cyclic capability dependency"):
        validate_asset_bootstrap_configuration(
            [catalog_fixture_capability(), quotes_fixture_capability()],
            dependency_policy=policy,
        )


def test_valid_configuration_is_accepted() -> None:
    validate_asset_bootstrap_configuration(
        [catalog_fixture_capability(), quotes_fixture_capability()]
    )
