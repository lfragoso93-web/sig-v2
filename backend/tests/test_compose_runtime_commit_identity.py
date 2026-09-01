from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPOSE = _REPO_ROOT / "docker-compose.yml"


def test_backend_runtime_commit_identity_is_explicit_in_compose() -> None:
    text = _COMPOSE.read_text(encoding="utf-8")

    assert "APP_COMMIT_SHA: ${APP_COMMIT_SHA:-unknown}" in text
    assert text.count("APP_COMMIT_SHA: ${APP_COMMIT_SHA:-unknown}") >= 2
