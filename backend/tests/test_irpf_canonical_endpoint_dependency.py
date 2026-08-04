"""Protege o endpoint canonico contra dependencia do motor fiscal legado."""

from pathlib import Path


def test_canonical_endpoint_uses_only_canonical_annual_service() -> None:
    router_source = Path("app/routers/irpf.py").read_text(encoding="utf-8")
    endpoint_start = router_source.index("async def get_canonical_irpf_assessment")
    endpoint_end = router_source.index("\n\n@router.get", endpoint_start)
    endpoint_source = router_source[endpoint_start:endpoint_end]

    assert "build_irpf_annual_assessment" in endpoint_source
    assert "calc_ganhos_capital" not in endpoint_source
    assert "generate_irpf_report" not in endpoint_source
    assert "IRPFReport" not in endpoint_source
