"""DB-first boundary for FX used by class snapshot rebuilds."""

from __future__ import annotations

from pathlib import Path

SERVICE_PATH = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "portfolio_class_snapshot_service.py"
)


def test_class_snapshot_service_uses_persisted_fx_reader_only() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")

    assert "app.services.fx_service" not in source
    assert "get_usd_brl_at_date" not in source
    assert "FALLBACK_RATE" not in source
    assert "load_usd_brl_rates_for_dates" in source
    assert source.index("fx_rates_by_date = await _load_required_usd_brl_rates") < (
        source.index("delete(PortfolioClassSnapshot)")
    )
