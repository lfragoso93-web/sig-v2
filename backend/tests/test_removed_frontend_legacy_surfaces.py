"""Gates dos placeholders e entradas paralelas removidos do frontend."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = ROOT / "frontend" / "src"
REMOVED_PATHS = (
    FRONTEND_SRC / "pages" / "AnalisePage.tsx",
    FRONTEND_SRC / "pages" / "HistoricoPage.tsx",
    FRONTEND_SRC / "pages" / "Login.tsx",
    FRONTEND_SRC / "pages" / "Register.tsx",
    FRONTEND_SRC / "router" / "index.tsx",
    FRONTEND_SRC / "components" / "ProtectedRoute.tsx",
)


def test_frontend_legacy_surfaces_are_not_available() -> None:
    assert [str(path) for path in REMOVED_PATHS if path.exists()] == []


def test_canonical_frontend_entries_remain_available() -> None:
    required_paths = (
        FRONTEND_SRC / "main.tsx",
        FRONTEND_SRC / "router" / "ProtectedRoute.tsx",
        FRONTEND_SRC / "pages" / "auth" / "LoginPage.tsx",
        FRONTEND_SRC / "pages" / "auth" / "RegisterPage.tsx",
        FRONTEND_SRC / "pages" / "MetasPage.tsx",
    )

    assert [str(path) for path in required_paths if not path.exists()] == []
