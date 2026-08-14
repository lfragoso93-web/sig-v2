"""Contrato estrutural do arquivo de configuração distribuído com o projeto."""
from pathlib import Path

from app.core.config import Settings


ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = ROOT / ".env.example"
COMPOSE = ROOT / "docker-compose.yml"


def _declared_variables() -> set[str]:
    variables: set[str] = set()
    for raw_line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        variables.add(line.split("=", 1)[0])
    return variables


def test_env_example_covers_every_application_setting() -> None:
    declared = _declared_variables()
    settings = set(Settings.model_fields)

    assert settings - declared == set()


def test_env_example_covers_operational_and_docker_variables() -> None:
    declared = _declared_variables()
    required = {
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "APP_PORT",
        "BACKEND_PORT",
        "APP_COMMIT_SHA",
        "VITE_API_URL",
        "ADMIN_EMAIL",
        "ADMIN_PASSWORD",
        "ADMIN_NAME",
        "ADMIN_SECRET",
        "SGI_BOOTSTRAP_COMMIT_SHA",
        "SGI_BOOTSTRAP_ENABLE_DIVIDENDS",
        "SGI_BOOTSTRAP_ENABLE_CORPORATE_EVENTS",
        "PRE_PROD_BRANCH",
        "PRE_PROD_COMMIT_SHA",
        "PRE_PROD_RESTORE_DATABASE_URL",
        "PRE_PROD_SYNC_DATABASE_URL",
    }

    assert required - declared == set()


def test_compose_forwards_frontend_api_url_to_build() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")

    assert "VITE_API_URL: ${VITE_API_URL:-}" in compose
