"""Contrato estático de escopo por carteira nos endpoints IRPF do usuário."""

from pathlib import Path


ROUTER_PATH = Path("app/routers/irpf.py")


def test_irpf_user_endpoints_validate_portfolio_ownership() -> None:
    source = ROUTER_PATH.read_text(encoding="utf-8")

    endpoint_names = (
        "list_anos",
        "get_irpf_report",
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
        assert "await _get_portfolio(portfolio_id, current_user, db)" in endpoint_source


def test_portfolio_lookup_is_scoped_by_current_user() -> None:
    source = ROUTER_PATH.read_text(encoding="utf-8")
    helper_start = source.index("async def _get_portfolio(")
    helper_end = source.index("\n@router.", helper_start)
    helper_source = source[helper_start:helper_end]

    assert "Portfolio.id == portfolio_id" in helper_source
    assert "Portfolio.user_id == user.id" in helper_source
    assert "status_code=404" in helper_source
