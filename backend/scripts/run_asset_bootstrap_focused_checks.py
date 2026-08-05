"""Executa o ciclo focado read-only do bootstrap canônico de ativos."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class CheckCommand:
    label: str
    command: tuple[str, ...]


CHECKS = (
    CheckCommand(
        label="asset bootstrap tests",
        command=(
            sys.executable,
            "-m",
            "pytest",
            "tests/test_asset_bootstrap_architecture_boundary.py",
            "tests/test_asset_bootstrap_capabilities.py",
            "tests/test_asset_bootstrap_configuration_validator.py",
            "tests/test_asset_bootstrap_coordinator.py",
            "tests/test_asset_bootstrap_dependency_policy.py",
            "tests/test_asset_bootstrap_full_pipeline.py",
            "tests/test_asset_bootstrap_identity.py",
            "tests/test_asset_bootstrap_plan_cli.py",
            "tests/test_asset_bootstrap_planner.py",
            "tests/test_asset_bootstrap_report_diff_cli.py",
            "tests/test_asset_bootstrap_report_diff_service.py",
            "-q",
        ),
    ),
    CheckCommand(
        label="compileall",
        command=(sys.executable, "-m", "compileall", "app", "tests"),
    ),
)


def main() -> int:
    for check in CHECKS:
        print(f"==> {check.label}")
        result = subprocess.run(check.command, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
