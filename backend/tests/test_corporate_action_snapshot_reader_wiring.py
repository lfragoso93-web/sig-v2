"""Gates arquiteturais dos consumidores de snapshot de eventos corporativos."""

from __future__ import annotations

from pathlib import Path

_SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"


def _source(name: str) -> str:
    return (_SERVICES / name).read_text(encoding="utf-8")


def test_portfolio_snapshot_uses_shared_canonical_reader() -> None:
    source = _source("portfolio_snapshot_service.py")

    assert "from app.services.corporate_action_position_reader import" in source
    assert "load_global_corporate_actions_by_ticker" in source
    assert "from app.models.corporate_event import" not in source
    assert "select(CorporateEvent)" not in source


def test_class_snapshot_uses_shared_canonical_reader() -> None:
    source = _source("portfolio_class_snapshot_service.py")

    assert "from app.services.corporate_action_position_reader import" in source
    assert "load_global_corporate_actions_by_ticker" in source
    assert "from app.models.corporate_event import" not in source
    assert "select(CorporateEvent)" not in source


def test_snapshot_projectors_remain_pure_and_database_agnostic() -> None:
    for filename in (
        "snapshot_position_projection.py",
        "class_snapshot_position_projection.py",
    ):
        source = _source(filename)
        assert "AsyncSession" not in source
        assert "CorporateEvent" not in source
        assert "select(" not in source
