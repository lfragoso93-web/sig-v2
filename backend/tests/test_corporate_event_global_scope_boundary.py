"""Impede que eventos corporativos globais voltem a depender de carteira."""

from __future__ import annotations

from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
_SERVICES = _BACKEND / "app" / "services"
_MODEL = _BACKEND / "app" / "models" / "corporate_event.py"
_ALLOWED_PORTFOLIO_SCOPE_MODULES = {
    "corporate_action_position_reader.py",
    "corporate_event_service.py",
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_writer_persists_only_global_corporate_events() -> None:
    source = _source(_SERVICES / "corporate_event_service.py")

    assert "portfolio_id=None" in source
    assert "portfolio_id=asset" not in source
    assert "portfolio_id=portfolio" not in source


def test_reader_excludes_legacy_portfolio_scoped_rows() -> None:
    source = _source(_SERVICES / "corporate_action_position_reader.py")

    assert "CorporateEvent.portfolio_id.is_(None)" in source


def test_portfolio_scope_stays_inside_compatibility_boundary() -> None:
    violations: list[str] = []

    for path in sorted(_SERVICES.glob("*.py")):
        if path.name in _ALLOWED_PORTFOLIO_SCOPE_MODULES:
            continue
        source = _source(path)
        imports_corporate_event = (
            "from app.models.corporate_event import" in source
            or "app.models.corporate_event" in source
        )
        if imports_corporate_event and ".portfolio_id" in source:
            violations.append(path.name)

    assert violations == [], (
        "CorporateEvent.portfolio_id é compatibilidade temporária e não pode "
        f"voltar aos consumidores financeiros: {violations}"
    )


def test_legacy_portfolio_relationship_is_explicitly_marked_for_contraction() -> None:
    source = _source(_MODEL)

    assert "portfolio_id = Column" in source
    assert "# Contratos legados preservados temporariamente" in source
