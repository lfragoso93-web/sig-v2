from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"


def test_sqlalchemy_21_installs_asyncio_runtime_dependency() -> None:
    runtime_requirements = (BACKEND_ROOT / "requirements.txt").read_text(
        encoding="utf-8"
    )
    test_requirements = (BACKEND_ROOT / "requirements-test.txt").read_text(
        encoding="utf-8"
    )

    assert "sqlalchemy[asyncio]==2.1.4" in runtime_requirements.splitlines()
    assert "sqlalchemy[asyncio,mypy]==2.1.4" in test_requirements.splitlines()


def test_sync_postgresql_urls_select_installed_psycopg2_driver() -> None:
    settings_source = (BACKEND_ROOT / "app/core/config.py").read_text(
        encoding="utf-8"
    )
    compose_source = (REPOSITORY_ROOT / "docker-compose.yml").read_text(
        encoding="utf-8"
    )
    environment_example = (REPOSITORY_ROOT / ".env.example").read_text(
        encoding="utf-8"
    )
    ci_workflow = (REPOSITORY_ROOT / ".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    )

    assert 'DATABASE_URL: str = "postgresql+psycopg2://' in settings_source
    assert "DATABASE_URL:       postgresql+psycopg2://" in compose_source
    assert "DATABASE_URL=postgresql+psycopg2://" in environment_example
    assert "DATABASE_URL: postgresql+psycopg2://" in ci_workflow


def test_entrypoint_postgres_probe_accepts_explicit_sqlalchemy_drivers() -> None:
    entrypoint = (BACKEND_ROOT / "entrypoint.sh").read_text(encoding="utf-8")

    assert "os.environ.get('ASYNC_DATABASE_URL')" in entrypoint
    assert "replace('postgresql+asyncpg', 'postgresql')" in entrypoint
    assert "replace('postgresql+psycopg2', 'postgresql')" in entrypoint


def test_treasury_migration_accepts_explicit_sqlalchemy_drivers() -> None:
    migration = (BACKEND_ROOT / "scripts/migrate_treasury.py").read_text(
        encoding="utf-8"
    )

    assert 'os.environ.get("ASYNC_DATABASE_URL")' in migration
    assert '"postgresql+asyncpg", "postgresql"' in migration
    assert '"postgresql+psycopg2", "postgresql"' in migration
