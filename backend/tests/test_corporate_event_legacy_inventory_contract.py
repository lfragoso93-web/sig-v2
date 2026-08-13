"""Protege o inventário read-only da compatibilidade histórica."""

from pathlib import Path

_SERVICE = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "corporate_event_legacy_inventory_service.py"
)


def test_inventory_is_read_only_and_exposes_contraction_metrics() -> None:
    source = _SERVICE.read_text(encoding="utf-8")

    assert "select(" in source
    assert "update(" not in source
    assert "delete(" not in source
    assert "commit(" not in source
    assert "portfolio_bound_legacy" in source
    assert "without_source_event_id" in source
    assert "without_effective_date" in source
    assert "without_quantity_factor" in source
