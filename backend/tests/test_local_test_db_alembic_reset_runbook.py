"""Protege o gate autorizado de reset do banco local de testes."""

from __future__ import annotations

from pathlib import Path

_RUNBOOK = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "runbooks"
    / "local-test-db-alembic-reset-validation.md"
)


def test_runbook_requires_explicit_local_test_database_scope() -> None:
    source = _RUNBOOK.read_text(encoding="utf-8").lower()

    assert "autorização explícita" in source
    assert "banco local de testes" in source
    assert "docker compose down -v" in source
    assert "alembic upgrade head" in source
    assert "alembic current" in source
    assert "alembic check" in source
    assert "python -m alembic" not in source


def test_runbook_blocks_operational_data_flows() -> None:
    source = _RUNBOOK.read_text(encoding="utf-8").lower()

    for required_prohibition in (
        "seed de ativos",
        "rebuild de mercado",
        "importação csv real",
        "pré-produção ou produção",
    ):
        assert required_prohibition in source
