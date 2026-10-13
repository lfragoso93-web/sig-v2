from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_backend_image_workflows_use_allowlisted_repository_context() -> None:
    workflow_paths = (
        REPOSITORY_ROOT / ".github/workflows/ci.yml",
        REPOSITORY_ROOT / ".github/workflows/security-deep-scan.yml",
    )

    for workflow_path in workflow_paths:
        source = workflow_path.read_text(encoding="utf-8")
        assert "context: ./backend" not in source
        assert "context: .\n          file: ./backend/Dockerfile" in source


def test_backend_docker_context_allowlists_packaged_contracts() -> None:
    dockerignore = (REPOSITORY_ROOT / ".dockerignore").read_text(encoding="utf-8")
    rules = dockerignore.splitlines()

    assert "*" in rules
    assert "!backend/**" in dockerignore
    assert "!.agents/**" in dockerignore
    assert "!README.md" in dockerignore
