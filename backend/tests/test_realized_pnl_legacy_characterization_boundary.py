"""Impede que o calculador histórico volte a ser tratado como runtime."""

from __future__ import annotations

from pathlib import Path

_SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"
_RUNTIME_SERVICE = _SERVICES / "realized_pnl_service.py"
_LEGACY_MODULE = _SERVICES / "realized_pnl_legacy_characterization.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_runtime_service_contains_no_parallel_position_calculator() -> None:
    source = _source(_RUNTIME_SERVICE)

    assert "state: dict" not in source
    assert "average_cost" not in source
    assert "OperationType" not in source
    assert "load_realized_pnl_by_ticker" in source


def test_runtime_service_does_not_reexport_legacy_calculators() -> None:
    source = _source(_RUNTIME_SERVICE)

    assert "realized_pnl_legacy_characterization" not in source
    assert '"calculate_realized_pnl"' not in source
    assert '"calculate_realized_pnl_by_ticker"' not in source


def test_legacy_calculator_is_explicitly_isolated() -> None:
    source = _source(_LEGACY_MODULE)

    assert "Caracterização legada" in source
    assert "não é uma fronteira de runtime" in source
    assert "realized_pnl_projection_reader" in source


def test_runtime_services_do_not_import_legacy_characterization() -> None:
    violations: list[str] = []

    for path in sorted(_SERVICES.glob("*.py")):
        if path.name == "realized_pnl_legacy_characterization.py":
            continue
        if "realized_pnl_legacy_characterization" in _source(path):
            violations.append(path.name)

    assert violations == [], (
        "o calculador histórico não pode ser importado pelo runtime: "
        f"{violations}"
    )
