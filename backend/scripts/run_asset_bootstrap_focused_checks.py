"""Executa o ciclo focado read-only do bootstrap canônico de ativos."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckCommand:
    label: str
    command: tuple[str, ...]


def _asset_bootstrap_test_paths() -> tuple[str, ...]:
    tests_dir = Path("tests")
    paths = tuple(
        str(path)
        for path in sorted(tests_dir.glob("test_asset_bootstrap*.py"))
        if path.is_file()
    )
    if not paths:
        raise RuntimeError("no asset bootstrap tests found")
    return paths


def _checks() -> tuple[CheckCommand, ...]:
    return (
        CheckCommand(
            label="asset bootstrap tests",
            command=(
                sys.executable,
                "-m",
                "pytest",
                *_asset_bootstrap_test_paths(),
                "-q",
            ),
        ),
        CheckCommand(
            label="compileall",
            command=(sys.executable, "-m", "compileall", "app", "tests"),
        ),
    )


def main() -> int:
    for check in _checks():
        print(f"==> {check.label}")
        result = subprocess.run(check.command, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
