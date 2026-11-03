from pathlib import Path


def test_irpf_bens_endpoint_uses_canonical_service() -> None:
    router = Path("app/routers/irpf.py").read_text(encoding="utf-8")

    assert (
        "from app.services.irpf_access_service import"
        in router
    )
    assert "return await read_irpf_assets(db, access, year)" in router
