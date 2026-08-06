"""Gates para a fixture PostgreSQL dos contratos legados isolados."""

from __future__ import annotations

from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE = (
    _BACKEND_ROOT
    / "tests"
    / "fixtures"
    / "alembic_legacy_contracts_synthetic.sql"
)


def test_fixture_is_transactional_and_non_persistent() -> None:
    source = _FIXTURE.read_text(encoding="utf-8")
    normalized = source.strip().upper()

    assert normalized.startswith("\\SET ON_ERROR_STOP ON\n\nBEGIN;")
    assert normalized.endswith("ROLLBACK;")
    assert "COMMIT;" not in normalized
    assert "DROP TABLE" not in normalized
    assert "TRUNCATE" not in normalized


def test_fixture_covers_all_isolated_legacy_contracts_and_foreign_keys() -> None:
    source = _FIXTURE.read_text(encoding="utf-8")

    assert "INSERT INTO users" in source
    assert "INSERT INTO portfolios" in source
    assert "INSERT INTO goals" in source
    assert "INSERT INTO irpf_records" in source
    assert "INSERT INTO irpf_losses" in source
    assert "INSERT INTO goal_allocations" in source
    assert ":fixture_user_id" in source
    assert ":fixture_goal_id" in source


def test_fixture_uses_psql_safe_assertions() -> None:
    source = _FIXTURE.read_text(encoding="utf-8")

    assert "DO $$" not in source
    assert source.count("SELECT 1 / CASE WHEN COUNT(*) = 1 THEN 1 ELSE 0 END") == 3
    assert "\\gset fixture_user_" in source
    assert "\\gset fixture_portfolio_" in source
    assert "\\gset fixture_goal_" in source
