"""Gates para comentários de portfolio_snapshots refletirem o schema migrado."""

from app.models.portfolio_snapshot import PortfolioSnapshot


def test_snapshot_historical_comments_match_initial_migration() -> None:
    columns = PortfolioSnapshot.__table__.c

    assert columns.market_value.comment == "Valor total de mercado na data (Σ qty × close_price)."
    assert columns.cost_basis.comment == "Custo total das posições abertas (Σ qty × avg_price)."
    assert columns.invested_total.comment == "Total aportado líquido acumulado até a data."
    assert columns.realized_pnl.comment == "Lucro/prejuízo realizado acumulado até a data."
    assert columns.unrealized_pnl.comment == "market_value - cost_basis."
    assert columns.total_pnl.comment == "realized_pnl + unrealized_pnl."
    assert columns.return_pct.comment == "total_pnl / invested_total × 100."


def test_snapshot_return_fields_do_not_invent_unmigrated_column_comments() -> None:
    columns = PortfolioSnapshot.__table__.c

    for name in (
        "net_external_flow",
        "dividends_day",
        "dividends_accumulated",
        "daily_return_pct",
        "accumulated_return_pct",
        "has_partial_prices",
        "return_is_estimated",
    ):
        assert columns[name].comment is None
