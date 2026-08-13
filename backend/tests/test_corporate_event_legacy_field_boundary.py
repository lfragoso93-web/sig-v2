"""Impede novos consumidores financeiros dos aliases legados de CorporateEvent."""

from __future__ import annotations

from pathlib import Path

_SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"
_ALLOWED_COMPATIBILITY_MODULES = {
    "corporate_action_position_reader.py",
    "corporate_event_legacy_backfill_plan_service.py",
    "corporate_event_legacy_dry_run_service.py",
    "corporate_event_legacy_inventory_service.py",
    "corporate_event_service.py",
    "ticker_change_event_service.py",
    "ticker_change_processor.py",
}
_LEGACY_ATTRIBUTES = (".event_date", ".ratio", ".brapi_event_id", ".raw_data")


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_historical_position_reader_uses_canonical_catalog_boundary() -> None:
    source = _source(_SERVICES / "historical_position_projection_reader.py")

    assert "from app.services.corporate_action_position_reader import" in source
    assert "load_global_corporate_actions_by_ticker" in source
    assert "from app.models.corporate_event import" not in source
    assert "select(CorporateEvent)" not in source


def test_legacy_corporate_event_fields_stay_inside_compatibility_boundary() -> None:
    violations: list[str] = []

    for path in sorted(_SERVICES.glob("*.py")):
        if path.name in _ALLOWED_COMPATIBILITY_MODULES:
            continue
        source = _source(path)
        imports_corporate_event = (
            "from app.models.corporate_event import" in source
            or "app.models.corporate_event" in source
        )
        if not imports_corporate_event:
            continue

        used = [attribute for attribute in _LEGACY_ATTRIBUTES if attribute in source]
        if used:
            violations.append(f"{path.name}: {', '.join(used)}")

    assert violations == [], (
        "aliases legados de CorporateEvent devem permanecer somente na camada "
        f"de compatibilidade: {violations}"
    )
