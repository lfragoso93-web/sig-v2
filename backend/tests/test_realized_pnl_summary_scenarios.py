from datetime import date
from types import SimpleNamespace

from app.services.portfolio_summary_service import (
    PortfolioSummaryInput,
    build_portfolio_summary,
)
from app.services.realized_pnl_legacy_characterization import calculate_realized_pnl


def _transaction(
    *,
    tx_id: int,
    operation: str,
    quantity: float,
    price: float,
    fees: float = 0.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=tx_id,
        date=date(2026, 1, tx_id),
        ticker="TEST3",
        asset_type="ACAO",
        operation=operation,
        quantity=quantity,
        price=price,
        fees=fees,
        currency="BRL",
        fx_rate=None,
    )


def test_partial_sale_reconciles_open_cost_and_realized_pnl_in_summary() -> None:
    realized_pnl = calculate_realized_pnl([
        _transaction(tx_id=1, operation="buy", quantity=10, price=100, fees=10),
        _transaction(tx_id=2, operation="sell", quantity=4, price=120, fees=4),
    ])

    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=606,
            current_value=660,
            realized_pnl=realized_pnl,
        )
    )

    assert realized_pnl == 72
    assert summary["total_investido"] == 606
    assert summary["ganho_nao_realizado"] == 54
    assert summary["ganho_realizado"] == 72
    assert summary["lucro_total"] == 126


def test_fully_closed_position_keeps_only_realized_pnl_in_summary() -> None:
    realized_pnl = calculate_realized_pnl([
        _transaction(tx_id=1, operation="buy", quantity=10, price=100, fees=10),
        _transaction(tx_id=2, operation="sell", quantity=10, price=110, fees=10),
    ])

    summary = build_portfolio_summary(
        PortfolioSummaryInput(
            total_invested=0,
            current_value=0,
            realized_pnl=realized_pnl,
        )
    )

    assert realized_pnl == 80
    assert summary["total_patrimonio"] == 0
    assert summary["total_investido"] == 0
    assert summary["ganho_nao_realizado"] == 0
    assert summary["ganho_realizado"] == 80
    assert summary["lucro_total"] == 80
