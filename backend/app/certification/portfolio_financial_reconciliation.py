"""Reconciliação financeira independente da carteira sintética da Issue #303.

Este módulo calcula expectativas exclusivamente a partir do fixture de certificação.
Ele não lê ORM, services de valuation, snapshots ou APIs e, portanto, funciona como
oráculo independente para comparar o read path canônico.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.certification.portfolio_seed_asset_policy import syntheticize_ticker
from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)

_ZERO = Decimal("0")
_MONEY = Decimal("0.01")


@dataclass(frozen=True)
class ReconciledHolding:
    ticker: str
    quantity: Decimal
    remaining_cost: Decimal
    realized_pnl: Decimal
    market_value: Decimal

    @property
    def open_pnl(self) -> Decimal:
        return (self.market_value - self.remaining_cost).quantize(_MONEY)


@dataclass(frozen=True)
class FinancialReconciliation:
    holdings: dict[str, ReconciledHolding]
    remaining_cost: Decimal
    market_value: Decimal
    realized_pnl: Decimal
    income: Decimal
    open_pnl: Decimal
    total_pnl: Decimal


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def calculate_independent_financial_reconciliation() -> FinancialReconciliation:
    """Calcula o resultado esperado sem reutilizar o motor financeiro do SGI."""
    fixture = load_portfolio_synthetic_certification_fixture()
    prices = fixture["market_prices"]["prices"]

    states: dict[str, dict[str, Decimal]] = {}
    for tx in fixture["transactions"]:
        source_ticker = str(tx["ticker"])
        ticker = syntheticize_ticker(source_ticker)
        state = states.setdefault(
            ticker,
            {"quantity": _ZERO, "cost": _ZERO, "realized": _ZERO},
        )
        quantity = _decimal(tx["quantity"])
        price = _decimal(tx["price"])
        fees = _decimal(tx.get("fees", "0"))
        if quantity <= 0 or price < 0 or fees < 0:
            raise ValueError(f"invalid synthetic transaction values for {source_ticker}")

        if str(tx["operation"]).lower() == "buy":
            state["quantity"] += quantity
            state["cost"] += quantity * price + fees
            continue

        if str(tx["operation"]).lower() != "sell":
            raise ValueError(f"unsupported synthetic operation: {tx['operation']}")
        if state["quantity"] <= 0 or quantity > state["quantity"]:
            raise ValueError(f"synthetic sale exceeds position for {source_ticker}")

        average_price = state["cost"] / state["quantity"]
        sold_cost = average_price * quantity
        state["realized"] += quantity * price - sold_cost - fees
        state["cost"] -= sold_cost
        state["quantity"] -= quantity
        if state["quantity"] == 0:
            state["cost"] = _ZERO

    holdings: dict[str, ReconciledHolding] = {}
    for source_ticker, raw_price in prices.items():
        ticker = syntheticize_ticker(source_ticker)
        state = states.get(ticker)
        if state is None or state["quantity"] <= 0:
            continue
        market_value = state["quantity"] * _decimal(raw_price)
        holdings[ticker] = ReconciledHolding(
            ticker=ticker,
            quantity=state["quantity"],
            remaining_cost=state["cost"].quantize(_MONEY),
            realized_pnl=state["realized"].quantize(_MONEY),
            market_value=market_value.quantize(_MONEY),
        )

    remaining_cost = sum((item.remaining_cost for item in holdings.values()), _ZERO)
    market_value = sum((item.market_value for item in holdings.values()), _ZERO)
    realized_pnl = sum((item.realized_pnl for item in holdings.values()), _ZERO)
    income = sum(
        (_decimal(event["gross_amount"]) for event in fixture.get("income_events", [])),
        _ZERO,
    )
    open_pnl = market_value - remaining_cost
    total_pnl = realized_pnl + open_pnl + income

    return FinancialReconciliation(
        holdings=holdings,
        remaining_cost=remaining_cost.quantize(_MONEY),
        market_value=market_value.quantize(_MONEY),
        realized_pnl=realized_pnl.quantize(_MONEY),
        income=income.quantize(_MONEY),
        open_pnl=open_pnl.quantize(_MONEY),
        total_pnl=total_pnl.quantize(_MONEY),
    )
