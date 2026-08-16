"""Contrato estrutural do arquivo de configuração distribuído com o projeto."""
from pathlib import Path

import pytest

from app.core.config import Settings


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
ENV_EXAMPLE = ROOT / ".env.example"
COMPOSE = ROOT / "docker-compose.yml"


def _require_repository_files() -> None:
    missing = [path for path in (ENV_EXAMPLE, COMPOSE) if not path.is_file()]
    if missing:
        pytest.skip(
            "contrato do repositorio indisponivel na imagem backend isolada: "
            + ", ".join(str(path) for path in missing)
        )


def _declared_variables() -> set[str]:
    _require_repository_files()
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
        "SGI_BOOTSTRAP_COMMIT_SHA",
        "SGI_BOOTSTRAP_ENABLE_DIVIDENDS",
        "SGI_BOOTSTRAP_ENABLE_CORPORATE_EVENTS",
        "PRE_PROD_BRANCH",
        "PRE_PROD_COMMIT_SHA",
        "PRE_PROD_RESTORE_DATABASE_URL",
        "PRE_PROD_SYNC_DATABASE_URL",
    }

    assert required - declared == set()


def test_legacy_admin_seed_is_not_shipped_by_backend() -> None:
    assert not (BACKEND / "seed_admin.py").exists()


def test_legacy_admin_env_contract_is_not_distributed() -> None:
    declared = _declared_variables()

    assert {"ADMIN_EMAIL", "ADMIN_PASSWORD", "ADMIN_NAME"}.isdisjoint(declared)


def test_python_backend_does_not_ship_empty_node_lockfile() -> None:
    assert not (BACKEND / "package-lock.json").exists()


def test_compose_forwards_frontend_api_url_to_build() -> None:
    _require_repository_files()
    compose = COMPOSE.read_text(encoding="utf-8")

    assert "VITE_API_URL: ${VITE_API_URL:-}" in compose
