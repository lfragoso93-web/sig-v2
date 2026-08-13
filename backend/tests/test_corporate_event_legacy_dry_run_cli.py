"""Garante a fronteira read-only da CLI de classificação do legado."""

from __future__ import annotations

from pathlib import Path

_CLI = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "cli"
    / "dry_run_corporate_event_legacy_classification.py"
)


def test_cli_exposes_versioned_dry_run_contract() -> None:
    source = _CLI.read_text(encoding="utf-8")

    assert '"corporate-event-legacy-dry-run.v1"' in source
    assert '"dry_run": True' in source
    assert '"read_only": True' in source
    assert "--sample-limit" in source


def test_cli_has_no_mutation_or_provider_access() -> None:
    source = _CLI.read_text(encoding="utf-8").lower()

    for forbidden in (
        ".commit(",
        ".delete(",
        ".add(",
        "brapi",
        "yahoo",
        "requests",
        "httpx",
    ):
        assert forbidden not in source
