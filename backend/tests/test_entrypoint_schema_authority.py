"""Garante que o entrypoint não crie tabelas fora do Alembic."""

from __future__ import annotations

from pathlib import Path


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_ENTRYPOINT = _BACKEND_ROOT / "entrypoint.sh"
_REPO_ROOT = _BACKEND_ROOT.parent


def test_entrypoint_uses_alembic_as_the_only_schema_authority() -> None:
    source = _ENTRYPOINT.read_text(encoding="utf-8")

    assert "alembic upgrade 022" in source
    assert "alembic upgrade heads" not in source
    assert "alembic heads" in source
    assert "alembic upgrade \"${RUNTIME_MIGRATION_TARGET}\"" in source
    assert "python -m scripts.create_superadmin" in source
    assert "table.create" not in source
    assert "checkfirst=True" not in source
    assert "OPTIONAL_TABLES" not in source
    assert "app.models.irpf" not in source


def test_entrypoint_starts_server_after_migrations() -> None:
    source = _ENTRYPOINT.read_text(encoding="utf-8")

    migrations_position = source.index("alembic upgrade \"${RUNTIME_MIGRATION_TARGET}\"")
    server_position = source.index("exec uvicorn")

    assert migrations_position < server_position


def test_compose_overlays_do_not_bypass_backend_entrypoint() -> None:
    for compose_file in ("docker-compose.prod.yml", "docker-compose.oci.yml"):
        source = (_REPO_ROOT / compose_file).read_text(encoding="utf-8")
        backend_block = source.split("  backend:", 1)[1].split("\n  frontend:", 1)[0]
        assert "command:" not in backend_block
