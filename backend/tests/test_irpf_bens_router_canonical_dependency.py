from pathlib import Path


def test_irpf_bens_endpoint_uses_canonical_service() -> None:
    router = Path("app/routers/irpf.py").read_text(encoding="utf-8")

    assert (
        "from app.services.irpf_bens_direitos_service import calc_bens_direitos"
        in router
    )
    assert "calc_bens_direitos," not in router.split(
        "from app.services.irpf_service import (", 1
    )[1].split(")", 1)[0]
