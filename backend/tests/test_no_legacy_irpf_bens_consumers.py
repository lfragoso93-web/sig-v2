import ast
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PRODUCTION_ROOTS = (
    _BACKEND_ROOT / "app" / "routers",
    _BACKEND_ROOT / "app" / "services",
    _BACKEND_ROOT / "app" / "cli",
)
_LEGACY_MODULE = "app.services.irpf_service"
_LEGACY_SYMBOL = "calc_bens_direitos"
_LEGACY_PATH = _BACKEND_ROOT / "app" / "services" / "irpf_service.py"


def _imports_legacy_symbol(source: str) -> bool:
    tree = ast.parse(source)
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == _LEGACY_MODULE
        and any(alias.name == _LEGACY_SYMBOL for alias in node.names)
        for node in ast.walk(tree)
    )


def _defines_legacy_symbol(source: str) -> bool:
    tree = ast.parse(source)
    return any(
        isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
        and node.name == _LEGACY_SYMBOL
        for node in ast.walk(tree)
    )


def test_no_production_consumer_imports_legacy_irpf_bens_reader() -> None:
    offenders: list[str] = []

    for root in _PRODUCTION_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            if _imports_legacy_symbol(source):
                offenders.append(str(path.relative_to(_BACKEND_ROOT)))

    assert offenders == [], (
        "Consumidores de produção não podem importar "
        f"{_LEGACY_SYMBOL} de irpf_service.py: {offenders}"
    )


def test_legacy_irpf_service_does_not_define_bens_reader() -> None:
    source = _LEGACY_PATH.read_text(encoding="utf-8")
    assert not _defines_legacy_symbol(source), (
        "irpf_service.py não pode voltar a definir calc_bens_direitos; "
        "use irpf_bens_direitos_service.py"
    )
