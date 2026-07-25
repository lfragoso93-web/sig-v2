"""Regression tests for non-destructive Treasury CLI help."""
from __future__ import annotations

import importlib
import sys

import pytest


@pytest.mark.parametrize(
    "module_name",
    (
        "app.cli.sync_treasury_catalog_v2",
        "app.cli.rebuild_treasury_official_prices",
        "app.cli.audit_treasury_catalog_v2",
        "app.cli.audit_treasury_canonical_assets",
    ),
)
def test_help_exits_before_database_access(
    module_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = importlib.import_module(module_name)

    def fail_database_access() -> None:
        raise AssertionError("--help must not open a database session")

    monkeypatch.setattr(module, "AsyncSessionLocal", fail_database_access)
    monkeypatch.setattr(sys, "argv", [module_name, "--help"])

    with pytest.raises(SystemExit) as exit_info:
        module.main()

    assert exit_info.value.code == 0
    assert "usage:" in capsys.readouterr().out
