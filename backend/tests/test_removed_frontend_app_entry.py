"""Gate contra a restauração da entrada React vazia e duplicada."""

from pathlib import Path

import pytest


BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
FRONTEND_SRC = ROOT / "frontend" / "src"
LEGACY_APP = FRONTEND_SRC / "App.tsx"
MAIN_ENTRY = FRONTEND_SRC / "main.tsx"


def _require_frontend_checkout() -> None:
    if not FRONTEND_SRC.is_dir():
        pytest.skip("frontend indisponivel na imagem backend isolada")


def test_legacy_frontend_app_entry_is_not_available() -> None:
    _require_frontend_checkout()
    assert not LEGACY_APP.exists()


def test_main_tsx_remains_the_single_router_entry() -> None:
    _require_frontend_checkout()
    source = MAIN_ENTRY.read_text(encoding="utf-8")

    assert "createBrowserRouter" in source
    assert "RouterProvider" in source
    assert "ReactDOM.createRoot" in source
    assert "from './App'" not in source
    assert 'from "./App"' not in source
