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
_ALLOWED_DEFINITION = _BACKEND_ROOT / "app" / "services" / "irpf_service.py"


def _imports_legacy_symbol(source: str) -> bool:
    tree = ast.parse(source)
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == _LEGACY_MODULE
        and any(alias.name == _LEGACY_SYMBOL for alias in node.names)
        for node in ast.walk(tree)
    )


def test_no_production_consumer_imports_legacy_irpf_bens_reader() -> None:
    offenders: list[str] = []

    for root in _PRODUCTION_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if path == _ALLOWED_DEFINITION:
                continue
            source = path.read_text(encoding="utf-8")
            if _imports_legacy_symbol(source):
                offenders.append(str(path.relative_to(_BACKEND_ROOT)))

    assert offenders == [], (
        "Consumidores de produção não podem voltar a importar "
        f"{_LEGACY_SYMBOL} de irpf_service.py: {offenders}"
    )
