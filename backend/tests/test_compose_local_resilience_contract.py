from pathlib import Path

import yaml


_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPOSE = _REPO_ROOT / "docker-compose.yml"


def _compose() -> dict:
    return yaml.safe_load(_COMPOSE.read_text(encoding="utf-8"))


def test_local_compose_persists_postgres_with_named_volume() -> None:
    compose = _compose()
    db_service = compose["services"]["db"]

    assert "postgres_data:/var/lib/postgresql/data" in db_service["volumes"]
    assert "postgres_data" in compose["volumes"]


def test_local_compose_healthchecks_gate_stateful_services() -> None:
    compose = _compose()
    db_service = compose["services"]["db"]
    backend_service = compose["services"]["backend"]
    frontend_service = compose["services"]["frontend"]

    assert "pg_isready" in " ".join(db_service["healthcheck"]["test"])
    assert (
        backend_service["depends_on"]["db"]["condition"] == "service_healthy"
    )
    assert (
        backend_service["depends_on"]["redis"]["condition"]
        == "service_healthy"
    )
    assert (
        "http://localhost:8000/health"
        in backend_service["healthcheck"]["test"]
    )
    assert (
        frontend_service["depends_on"]["backend"]["condition"]
        == "service_healthy"
    )


def test_local_compose_keeps_redis_ephemeral_cache_only() -> None:
    compose = _compose()
    redis_service = compose["services"]["redis"]

    assert redis_service["command"] == (
        "redis-server --maxmemory 64mb --maxmemory-policy allkeys-lru"
    )
    assert "redis_data" not in compose["volumes"]
    assert "volumes" not in redis_service
