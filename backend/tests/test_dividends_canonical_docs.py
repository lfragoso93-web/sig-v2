"""Regression guards for the live canonical dividends documentation."""

from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not (REPOSITORY_ROOT / "README.md").is_file(),
    reason="live repository documents are absent from the backend-only image",
)

LIVE_DOCUMENTS = (
    "README.md",
    "ROADMAP.md",
    "docs/canonical-data.md",
    "docs/architecture.md",
    "docs/operations.md",
    "docs/PRE_PROD_REBUILD_RUNBOOK.md",
)

OBSOLETE_CURRENT_STATE = (
    "Proventos devem ser materializados por carteira antes dos snapshots.",
    "sincronizar e materializar proventos",
    "A CLI, o comparador e o wrapper v1 permanecem no repositório",
    "Contrato `pre-prod-dividends-seed.v1` publicado",
    "implementação e execução real pendentes",
)


def _read(relative_path: str) -> str:
    return (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")


def test_live_documents_do_not_describe_materialization_as_current() -> None:
    combined = "\n".join(_read(path) for path in LIVE_DOCUMENTS)

    for obsolete_text in OBSOLETE_CURRENT_STATE:
        assert obsolete_text not in combined


def test_live_documents_publish_the_canonical_v2_boundary() -> None:
    readme = _read("README.md")
    roadmap = _read("ROADMAP.md")
    canonical_data = _read("docs/canonical-data.md")
    rebuild_runbook = _read("docs/PRE_PROD_REBUILD_RUNBOOK.md")
    normalized_runbook = " ".join(rebuild_runbook.split())

    assert "pre-prod-dividends-seed.v2" in readme
    assert "pre-prod-dividends-seed.v2" in roadmap
    assert "`asset_dividends`" in canonical_data
    assert "calculados sob demanda" in readme
    assert "Nenhuma coleta ou leitura materializa direitos" in canonical_data
    assert "duas execuções reais controladas permanecem pendentes" in normalized_runbook
    assert "20260731_drop_legacy_divs" in rebuild_runbook
