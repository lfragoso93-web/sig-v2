"""Reconciliação financeira independente da carteira sintética da Issue #303.

Este módulo calcula expectativas exclusivamente a partir do fixture de certificação.
Ele não lê ORM, services de valuation, snapshots ou APIs e, portanto, funciona como
oráculo independente para comparar o read path canônico.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.certification.portfolio_synthetic_fixture import (
    load_portfolio_synthetic_certification_fixture,
)

_ZERO = Decimal("0")
_MONEY = Decimal("0.01")
_SYNTHETIC_PREFIX = "CERT303-"


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


def _persisted_ticker(source_ticker: object) -> str:
    normalized = str(source_ticker or "").strip().upper()
    if not normalized or normalized.startswith(_SYNTHETIC_PREFIX):
        raise ValueError("invalid source ticker in synthetic reconciliation fixture")
    return f"{_SYNTHETIC_PREFIX}{normalized}"


def assert_declared_financial_expectations(
    fixture: dict,
    actual: FinancialReconciliation,
) -> None:
    """Falha se o oráculo independente divergir do bloco expected do fixture."""
    declared = fixture["expected"]
    failures: list[str] = []

    expected_tickers = {
        _persisted_ticker(source_ticker) for source_ticker in declared["holdings"]
    }
    if set(actual.holdings) != expected_tickers:
        failures.append("holding-set")

    for source_ticker, expected in declared["holdings"].items():
        ticker = _persisted_ticker(source_ticker)
        holding = actual.holdings.get(ticker)
        if holding is None:
            failures.append(f"{ticker}:missing")
            continue
        comparisons = {
            "quantity": (holding.quantity, _decimal(expected["quantity"])),
            "remaining_cost": (
                holding.remaining_cost,
                _decimal(expected["remaining_cost"]),
            ),
            "realized_pnl": (holding.realized_pnl, _decimal(expected["realized_pnl"])),
            "market_value": (holding.market_value, _decimal(expected["market_value"])),
        }
        for field, (observed, wanted) in comparisons.items():
            if observed != wanted:
                failures.append(
                    f"{ticker}:{field}:actual={observed}:expected={wanted}"
                )

    totals = declared["totals"]
    total_comparisons = {
        "remaining_cost": (actual.remaining_cost, _decimal(totals["remaining_cost"])),
        "market_value": (actual.market_value, _decimal(totals["market_value"])),
        "realized_pnl": (actual.realized_pnl, _decimal(totals["realized_pnl"])),
        "income": (actual.income, _decimal(totals["income"])),
        "open_pnl": (actual.open_pnl, _decimal(totals["open_pnl"])),
        "total_pnl": (actual.total_pnl, _decimal(totals["total_pnl"])),
    }
    for field, (observed, wanted) in total_comparisons.items():
        if observed != wanted:
            failures.append(f"totals:{field}:actual={observed}:expected={wanted}")

    if failures:
        raise ValueError("declared financial expectations drift: " + "; ".join(failures))


def calculate_independent_financial_reconciliation() -> FinancialReconciliation:
    """Calcula o resultado esperado sem reutilizar o motor financeiro do SGI."""
    fixture = load_portfolio_synthetic_certification_fixture()
    prices = fixture["market_prices"]["prices"]

    states: dict[str, dict[str, Decimal]] = {}
    for tx in fixture["transactions"]:
        source_ticker = str(tx["ticker"])
        ticker = _persisted_ticker(source_ticker)
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

    price_by_ticker = {
        _persisted_ticker(source_ticker): _decimal(raw_price)
        for source_ticker, raw_price in prices.items()
    }
    holdings: dict[str, ReconciledHolding] = {}
    for ticker, state in states.items():
        if state["quantity"] <= 0:
            continue
        if ticker not in price_by_ticker:
            raise ValueError(f"missing expected market price for {ticker}")
        market_value = state["quantity"] * price_by_ticker[ticker]
        holdings[ticker] = ReconciledHolding(
            ticker=ticker,
            quantity=state["quantity"],
            remaining_cost=state["cost"].quantize(_MONEY),
            realized_pnl=state["realized"].quantize(_MONEY),
            market_value=market_value.quantize(_MONEY),
        )

    remaining_cost = sum((item.remaining_cost for item in holdings.values()), _ZERO)
    market_value = sum((item.market_value for item in holdings.values()), _ZERO)
    realized_pnl = sum((state["realized"] for state in states.values()), _ZERO)
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