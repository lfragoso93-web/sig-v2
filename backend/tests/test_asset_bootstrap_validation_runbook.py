"""Protege o roteiro focado contra caminhos de artefato invisíveis ao container."""

from __future__ import annotations

from pathlib import Path

_RUNBOOK = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "runbooks"
    / "asset-bootstrap-focused-validation.md"
)


def test_runbook_compares_generated_artifacts_on_host() -> None:
    source = _RUNBOOK.read_text(encoding="utf-8")

    assert "Push-Location backend" in source
    assert "python -m app.cli.compare_asset_bootstrap_reports" in source
    assert "backend/artifacts/asset-bootstrap/plan-1.json" in source
    assert "backend/artifacts/asset-bootstrap/plan-2.json" in source


def test_runbook_does_not_compare_host_files_in_fresh_container() -> None:
    source = _RUNBOOK.read_text(encoding="utf-8")
    comparison_section = source.split("## 6. Comparar os artefatos offline no host", 1)[1]

    assert "docker compose run --rm backend" not in comparison_section.split(
        "## Critérios de aprovação", 1
    )[0]
