from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPOSE = _REPO_ROOT / "docker-compose.yml"
_BACKEND_DOCKERFILE = _REPO_ROOT / "backend" / "Dockerfile"


def test_backend_runtime_commit_identity_is_explicit_in_compose() -> None:
    text = _COMPOSE.read_text(encoding="utf-8")

    assert "APP_COMMIT_SHA: ${APP_COMMIT_SHA:-unknown}" in text
    assert text.count("APP_COMMIT_SHA: ${APP_COMMIT_SHA:-unknown}") >= 2


def test_backend_runtime_certification_identity_is_explicit_in_compose() -> None:
    text = _COMPOSE.read_text(encoding="utf-8")

    assert "APP_BRANCH: ${APP_BRANCH:-unknown}" in text
    assert "REAL_DATASET_REFERENCE: ${REAL_DATASET_REFERENCE:-}" in text


def test_backend_commit_identity_does_not_invalidate_filesystem_layers() -> None:
    text = _BACKEND_DOCKERFILE.read_text(encoding="utf-8")

    identity_position = text.index("ARG APP_COMMIT_SHA=unknown")

    assert text.index("apt-get upgrade -y") < identity_position
    assert text.index("COPY --chown=app:app . .") < identity_position
    assert text.index("LABEL org.opencontainers.image.revision") > identity_position
