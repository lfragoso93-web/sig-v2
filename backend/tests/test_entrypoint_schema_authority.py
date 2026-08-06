"""Garante que o entrypoint não crie tabelas fora do Alembic."""

from __future__ import annotations

from pathlib import Path


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_ENTRYPOINT = _BACKEND_ROOT / "entrypoint.sh"


def test_entrypoint_uses_alembic_as_the_only_schema_authority() -> None:
    source = _ENTRYPOINT.read_text(encoding="utf-8")

    assert "alembic upgrade 022" in source
    assert "alembic upgrade heads" in source
    assert "table.create" not in source
    assert "checkfirst=True" not in source
    assert "OPTIONAL_TABLES" not in source
    assert "app.models.irpf" not in source


def test_entrypoint_starts_server_after_migrations() -> None:
    source = _ENTRYPOINT.read_text(encoding="utf-8")

    migrations_position = source.index("alembic upgrade heads")
    server_position = source.index("exec uvicorn")

    assert migrations_position < server_position
