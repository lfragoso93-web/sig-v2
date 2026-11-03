"""Contrato estático de escopo por carteira nos endpoints IRPF do usuário."""

from pathlib import Path

ROUTER_PATH = Path("app/routers/irpf.py")


def test_irpf_user_endpoints_validate_portfolio_ownership() -> None:
    source = ROUTER_PATH.read_text(encoding="utf-8")

    endpoint_names = (
        "list_anos",
        "get_irpf_report",
        "get_canonical_irpf_assessment",
        "get_canonical_irpf_assets",
        "get_canonical_irpf_capital_gains",
        "get_canonical_irpf_income",
        "download_irpf_pdf",
        "download_irpf_csv",
        "get_bens_direitos",
        "get_ganhos_capital",
        "get_rendimentos",
    )

    for index, endpoint_name in enumerate(endpoint_names):
        start = source.index(f"async def {endpoint_name}(")
        end = (
            source.index("\n@router.", start + 1)
            if index < len(endpoint_names) - 1
            else len(source)
        )
        endpoint_source = source[start:end]
        assert "_access_context(portfolio_id, current_user)" in endpoint_source


def test_context_is_authorized_at_service_boundary() -> None:
    source = ROUTER_PATH.read_text(encoding="utf-8")
    helper_start = source.index("def _access_context(")
    helper_end = source.index("\n@router.", helper_start)
    helper_source = source[helper_start:helper_end]

    assert "PortfolioAccessContext.for_user" in helper_source
    assert "READ_PORTFOLIO_IRPF" in helper_source
    assert "status_code=404" in helper_source
    assert "require_irpf_access(db, access)" in source
