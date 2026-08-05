"""Caracteriza identidade auditável na execução simulada do bootstrap."""

from __future__ import annotations

import asyncio

from app.services.asset_bootstrap_contracts import (
    AssetBootstrapExecutionIdentity,
    AssetBootstrapRequest,
)
from app.services.asset_bootstrap_coordinator import AssetBootstrapCoordinator
from tests.fixtures.asset_bootstrap_capabilities import catalog_fixture_capability


def test_execution_report_normalizes_identity() -> None:
    report = asyncio.run(
        AssetBootstrapCoordinator([catalog_fixture_capability()]).execute(
            AssetBootstrapRequest(ticker=" petr4 ", asset_type=" acao "),
            identity=AssetBootstrapExecutionIdentity(
                run_id=" run-001 ",
                branch=" stable-15jun ",
                commit_sha=" ABCDEF ",
            ),
        )
    )

    assert report.identity is not None
    assert report.identity.run_id == "run-001"
    assert report.identity.branch == "stable-15jun"
    assert report.identity.commit_sha == "abcdef"
    assert report.to_dict()["identity"] == {
        "run_id": "run-001",
        "branch": "stable-15jun",
        "commit_sha": "abcdef",
    }


def test_execution_report_preserves_backward_compatibility_without_identity() -> None:
    report = asyncio.run(
        AssetBootstrapCoordinator([catalog_fixture_capability()]).execute(
            AssetBootstrapRequest(ticker="PETR4", asset_type="ACAO")
        )
    )

    assert report.identity is None
    assert "identity" not in report.to_dict()
