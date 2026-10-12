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

    assert "sqlalchemy[asyncio]==2.1.2" in runtime_requirements.splitlines()
    assert "sqlalchemy[asyncio,mypy]==2.1.2" in test_requirements.splitlines()


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

    assert 'DATABASE_URL: str = "postgresql+psycopg2://' in settings_source
    assert "DATABASE_URL:       postgresql+psycopg2://" in compose_source
    assert "DATABASE_URL=postgresql+psycopg2://" in environment_example
