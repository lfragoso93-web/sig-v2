"""Garante que a CLI de inventário permaneça estritamente read-only."""

from __future__ import annotations

from pathlib import Path

_CLI = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "cli"
    / "audit_corporate_event_legacy_inventory.py"
)


def test_cli_exposes_versioned_read_only_json_contract() -> None:
    source = _CLI.read_text(encoding="utf-8")

    assert '"corporate-event-legacy-inventory.v1"' in source
    assert '"read_only": True' in source
    assert "json.dumps" in source
    assert "sort_keys=True" in source


def test_cli_does_not_mutate_or_call_external_providers() -> None:
    source = _CLI.read_text(encoding="utf-8")

    for forbidden in (
        ".commit(",
        ".delete(",
        ".add(",
        "brapi",
        "yahoo",
        "requests",
        "httpx",
    ):
        assert forbidden not in source.lower()
