"""Gate contra reintroducao do placeholder HTTP do futuro modulo de Analise."""

from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
ANALYSIS_ROUTER = BACKEND / "app" / "routers" / "analysis.py"
MAIN = BACKEND / "app" / "main.py"


def test_analysis_placeholder_router_is_absent() -> None:
    assert not ANALYSIS_ROUTER.exists()


def test_main_does_not_mount_analysis_placeholder() -> None:
    source = MAIN.read_text(encoding="utf-8")

    assert "    analysis,\n" not in source
    assert "analysis.router" not in source
    assert 'prefix=f"{PREFIX}/analysis"' not in source
