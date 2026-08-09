from __future__ import annotations

from pathlib import Path


def test_treasury_reconciliation_cannot_create_assets() -> None:
    source = Path("app/services/treasury_reconciliation_service.py").read_text(
        encoding="utf-8"
    )

    assert "db.add(" not in source
    assert "_ensure_asset" not in source
    assert "Asset(" not in source
    assert "nunca criar ativos" in source
