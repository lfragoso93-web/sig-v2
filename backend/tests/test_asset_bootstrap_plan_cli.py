"""Regressões da CLI read-only de planejamento do bootstrap."""

from __future__ import annotations

from pathlib import Path


_CLI = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "cli"
    / "plan_asset_bootstrap.py"
)


def test_plan_cli_does_not_import_test_fixtures_or_runtime_providers() -> None:
    source = _CLI.read_text(encoding="utf-8").lower()

    for forbidden in (
        "app.tests",
        "tests.fixtures",
        "brapi",
        "yahoo",
        "sqlalchemy",
        "asyncsession",
        "app.models",
        "requests",
        "httpx",
    ):
        assert forbidden not in source


def test_plan_cli_remains_read_only() -> None:
    source = _CLI.read_text(encoding="utf-8").lower()

    for forbidden in (
        ".commit(",
        ".add(",
        ".delete(",
        "alembic",
        "seed",
        "rebuild",
    ):
        assert forbidden not in source

    assert "plan_asset_bootstrap" in source
    assert "writes_executed" not in source
