"""Regressões do runner focado do bootstrap canônico de ativos."""

from __future__ import annotations

from pathlib import Path

_RUNNER = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_asset_bootstrap_focused_checks.py"
)


def test_runner_discovers_existing_asset_bootstrap_tests() -> None:
    source = _RUNNER.read_text(encoding="utf-8")

    assert 'glob("test_asset_bootstrap*.py")' in source
    assert "test_asset_bootstrap_capabilities.py" not in source
    assert "test_asset_bootstrap_coordinator.py" not in source
    assert "test_asset_bootstrap_full_pipeline.py" not in source


def test_runner_remains_read_only() -> None:
    source = _RUNNER.read_text(encoding="utf-8").lower()

    for forbidden in (
        "brapi",
        "yahoo",
        ".commit(",
        ".add(",
        ".delete(",
        "alembic upgrade",
        "seed",
        "rebuild",
    ):
        assert forbidden not in source
