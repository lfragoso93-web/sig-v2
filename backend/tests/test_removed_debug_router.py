"""Gate de segurança contra a reintrodução do router administrativo de debug."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEBUG_ROUTER = ROOT / "app" / "routers" / "debug.py"
MAIN = ROOT / "app" / "main.py"
CONFIG = ROOT / "app" / "core" / "config.py"
ENV_EXAMPLE = ROOT.parent / ".env.example"


def test_debug_router_is_not_available() -> None:
    assert not DEBUG_ROUTER.exists()


def test_application_does_not_mount_debug_surface() -> None:
    source = MAIN.read_text(encoding="utf-8")

    assert "debug.router" not in source
    assert 'tags=["debug"]' not in source
    assert 'prefix=f"{PREFIX}/debug"' not in source


def test_debug_secret_and_rate_limit_are_not_public_configuration() -> None:
    config = CONFIG.read_text(encoding="utf-8")
    env_example = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "ADMIN_SECRET" not in config
    assert "DEBUG_RATE_LIMIT" not in config
    assert "ADMIN_SECRET=" not in env_example
    assert "DEBUG_RATE_LIMIT=" not in env_example
