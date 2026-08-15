"""Gate contra a restauração da entrada React vazia e duplicada."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEGACY_APP = ROOT / "frontend" / "src" / "App.tsx"
MAIN_ENTRY = ROOT / "frontend" / "src" / "main.tsx"


def test_legacy_frontend_app_entry_is_not_available() -> None:
    assert not LEGACY_APP.exists()


def test_main_tsx_remains_the_single_router_entry() -> None:
    source = MAIN_ENTRY.read_text(encoding="utf-8")

    assert "createBrowserRouter" in source
    assert "RouterProvider" in source
    assert "ReactDOM.createRoot" in source
    assert "from './App'" not in source
    assert 'from "./App"' not in source
