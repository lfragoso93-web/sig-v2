"""Gates de governança para a deriva global entre Alembic e MetaData."""

from __future__ import annotations

from pathlib import Path

_INVENTORY = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "ALEMBIC_METADATA_DRIFT_INVENTORY_2026-08.md"
)


def test_inventory_blocks_monolithic_autogenerate() -> None:
    source = _INVENTORY.read_text(encoding="utf-8").lower()

    assert "não gerar migration automática com o diff completo" in source
    assert "não remover tabelas apenas porque estão ausentes" in source
    assert "um domínio ou contrato por commit" in source
    assert "fixture sintética" in source


def test_inventory_tracks_high_risk_schema_objects() -> None:
    source = _INVENTORY.read_text(encoding="utf-8")

    for required_object in (
        "app_config",
        "irpf_reports",
        "fx_rates",
        "irpf_records",
        "irpf_losses",
        "goal_allocations",
        "assets",
        "asset_dividends",
        "corporate_events",
        "transactions",
    ):
        assert f"`{required_object}`" in source


def test_inventory_keeps_global_drift_separate_from_corporate_bootstrap() -> None:
    source = _INVENTORY.read_text(encoding="utf-8").lower()

    assert "a cadeia de revisions está funcional" in source
    assert "bloqueio é de convergência global" in source
    assert "#129" in source
    assert "#241" in source
