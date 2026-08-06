"""Regressões da CLI offline de comparação do bootstrap."""

from __future__ import annotations

import json
from pathlib import Path

from app.cli.compare_asset_bootstrap_reports import _load_report


def _report() -> dict[str, object]:
    return {
        "ticker": "PETR4",
        "asset_type": "ACAO",
        "ok": False,
        "capabilities": [],
        "coverage": {
            "total_capabilities": 0,
            "successful_capabilities": 0,
            "failed_capabilities": [],
            "blocked_capabilities": [],
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "warnings": 0,
            "errors": 0,
        },
    }


def test_loader_accepts_plain_report(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    report = _report()
    path.write_text(json.dumps(report), encoding="utf-8")

    assert _load_report(path) == report


def test_loader_unwraps_versioned_plan_envelope(tmp_path: Path) -> None:
    path = tmp_path / "plan.json"
    report = _report()
    path.write_text(
        json.dumps(
            {
                "schema_version": "asset-bootstrap-plan.v1",
                "mode": "plan",
                "dry_run": True,
                "read_only": True,
                "writes_executed": False,
                "report": report,
            }
        ),
        encoding="utf-8",
    )

    assert _load_report(path) == report
