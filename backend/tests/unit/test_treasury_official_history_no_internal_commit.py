from __future__ import annotations

from pathlib import Path


SERVICE = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "services"
    / "treasury_official_history_service.py"
)


def test_history_service_has_single_explicit_commit_gate() -> None:
    source = SERVICE.read_text(encoding="utf-8")

    assert source.count("await db.commit()") == 1
    assert "if commit:\n        await db.commit()" in source
