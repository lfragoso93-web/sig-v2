from datetime import date
from types import SimpleNamespace

from app.services.portfolio_summary_service import (
    PortfolioSummaryInput,
    build_portfolio_summary,
)
from app.services.realized_pnl_service import calculate_realized_pnl


def _tx(
    *,
    ticker: str,
    operation: str,
    quantity: float,
    price: float,
    fees: float = 0.0,
    tx_date: date = date(2024, 1, 1),
    asset_type: str = "ACAO",
    currency: str = "BRL",
    fx_rate: float | None = None,
    tx_id: int = 1,
):
    return SimpleNamespace(
        id=tx_id,
        ticker=ticker,
        operation=operation,
        quantity=quantity,
        price=price,
        fees=fees,
        date=tx_date,
        asset_type=asset_type,
        currency=currency,
        fx_rate=fx_rate,
    )


def test_result_includes_realized_unrealized_and_all_dividends():
    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=1_000,
            current_value=900,
            realized_pnl=250,
            total_dividends=75,
            dividends_12m=30,
        )
    )

    assert summary["ganho_nao_realizado"] == -100
    assert summary["ganho_realizado"] == 250
    assert summary["total_proventos"] == 75
    assert summary["lucro_total"] == 225


def test_realized_pnl_preserves_closed_position_and_deducts_sell_fee():
    transactions = [
        _tx(
            ticker="TEST3",
            operation="buy",
            quantity=10,
            price=10,
            fees=2,
            tx_date=date(2024, 1, 1),
            tx_id=1,
        ),
        _tx(
            ticker="TEST3",
            operation="sell",
            quantity=10,
            price=15,
            fees=3,
            tx_date=date(2024, 2, 1),
            tx_id=2,
        ),
    ]

    # Custo total = 102; venda liquida = 147; ganho realizado = 45.
    assert calculate_realized_pnl(transactions) == 45


def test_realized_pnl_uses_saved_fx_rate_for_international_assets():
    transactions = [
        _tx(
            ticker="AAPL",
            operation="buy",
            quantity=1,
            price=100,
            fees=1,
            asset_type="STOCK",
            currency="USD",
            fx_rate=5,
            tx_date=date(2024, 1, 1),
            tx_id=1,
        ),
        _tx(
            ticker="AAPL",
            operation="sell",
            quantity=1,
            price=120,
            fees=1,
            asset_type="STOCK",
            currency="USD",
            fx_rate=5,
            tx_date=date(2024, 2, 1),
            tx_id=2,
        ),
    ]

    # Compra = 505 BRL; venda liquida = 595 BRL.
    assert calculate_realized_pnl(transactions) == 90
