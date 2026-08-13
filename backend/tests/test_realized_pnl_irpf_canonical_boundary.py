"""Gates arquiteturais para realizações e apuração fiscal canônicas."""

from __future__ import annotations

from pathlib import Path

_SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"


def _source(filename: str) -> str:
    return (_SERVICES / filename).read_text(encoding="utf-8")


def test_realized_pnl_runtime_delegates_to_canonical_projection_reader() -> None:
    source = _source("realized_pnl_service.py")

    assert "from app.services.realized_pnl_projection_reader import" in source
    assert "load_realized_pnl_by_ticker" in source
    assert "select(Transaction)" not in source
    assert "from app.models.corporate_event import" not in source


def test_realized_disposals_use_global_corporate_action_reader() -> None:
    source = _source("realized_pnl_projection_reader.py")

    assert "from app.services.corporate_action_position_reader import" in source
    assert "load_global_corporate_actions_by_ticker" in source
    assert "project_transaction_timelines" in source
    assert "from app.models.corporate_event import" not in source


def test_integrated_irpf_consumes_canonical_realized_disposals() -> None:
    source = _source("irpf_annual_integrated_assessment_service.py")

    assert "from app.services.realized_pnl_projection_reader import" in source
    assert "load_realized_disposals" in source
    assert "from app.services.irpf_realized_disposal_tax_adapter import" in source
    assert "from app.models.corporate_event import" not in source


def test_fiscal_adapter_does_not_recalculate_financial_projection() -> None:
    source = _source("irpf_realized_disposal_tax_adapter.py")

    assert "CanonicalRealizedDisposal" in source
    assert "select(" not in source
    assert "AsyncSession" not in source
    assert "CorporateEvent" not in source
