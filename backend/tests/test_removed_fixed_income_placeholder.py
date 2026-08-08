from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "app"
MAIN_PATH = APP_ROOT / "main.py"
REMOVED_ROUTER_PATH = APP_ROOT / "routers" / "fixed_income.py"


def test_fixed_income_placeholder_router_is_removed() -> None:
    assert not REMOVED_ROUTER_PATH.exists()


def test_main_does_not_register_fixed_income_placeholder() -> None:
    source = MAIN_PATH.read_text(encoding="utf-8")
    assert "fixed_income" not in source
    assert "/fixed-income" not in source
