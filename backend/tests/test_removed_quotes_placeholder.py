from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = BACKEND_ROOT / "app" / "main.py"
QUOTES_ROUTER_PATH = BACKEND_ROOT / "app" / "routers" / "quotes.py"


def test_quotes_placeholder_router_is_removed() -> None:
    assert not QUOTES_ROUTER_PATH.exists()


def test_main_does_not_register_quotes_placeholder() -> None:
    source = MAIN_PATH.read_text(encoding="utf-8")
    assert "quotes.router" not in source
    assert 'prefix=f"{PREFIX}/quotes"' not in source
