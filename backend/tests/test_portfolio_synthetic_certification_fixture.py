import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from io import StringIO
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.csv_import_service import (
    CSV_TEMPLATE_HEADERS,
    parse_csv_content,
)


FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "portfolio_synthetic_certification_v1.json"
)
CENT = Decimal("0.01")
QTY = Decimal("0.00000001")


@dataclass
class Lot:
    quantity: Decimal
    unit_cost: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _quantity(value: Decimal) -> Decimal:
    return value.quantize(QTY)


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _to_csv(transactions: list[dict[str, str]]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_TEMPLATE_HEADERS)
    writer.writeheader()
    writer.writerows(transactions)
    return output.getvalue()


def _reconcile(
    transactions: list[dict[str, str]],
    prices: dict[str, str],
) -> dict:
    lots: dict[str, list[Lot]] = defaultdict(list)
    realized: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for tx in sorted(transactions, key=lambda row: row["date"]):
        ticker = tx["ticker"]
        quantity = Decimal(tx["quantity"])
        price = Decimal(tx["price"])
        fees = Decimal(tx["fees"])

        if tx["operation"] == "buy":
            lots[ticker].append(
                Lot(
                    quantity=quantity,
                    unit_cost=(quantity * price + fees) / quantity,
                )
            )
            continue

        remaining_to_sell = quantity
        proceeds = quantity * price - fees
        cost_released = Decimal("0")

        while remaining_to_sell > 0:
            current_lot = lots[ticker][0]
            consumed = min(current_lot.quantity, remaining_to_sell)
            cost_released += consumed * current_lot.unit_cost
            current_lot.quantity -= consumed
            remaining_to_sell -= consumed
            if current_lot.quantity == 0:
                lots[ticker].pop(0)

        realized[ticker] += proceeds - cost_released

    holdings = {}
    for ticker, ticker_lots in lots.items():
        quantity = sum((lot.quantity for lot in ticker_lots), Decimal("0"))
        remaining_cost = sum(
            (lot.quantity * lot.unit_cost for lot in ticker_lots),
            Decimal("0"),
        )
        market_value = quantity * Decimal(prices[ticker])
        holdings[ticker] = {
            "quantity": f"{_quantity(quantity):.8f}",
            "remaining_cost": f"{_money(remaining_cost):.2f}",
            "realized_pnl": f"{_money(realized[ticker]):.2f}",
            "market_value": f"{_money(market_value):.2f}",
        }

    totals = {
        "remaining_cost": sum(
            Decimal(item["remaining_cost"]) for item in holdings.values()
        ),
        "market_value": sum(
            Decimal(item["market_value"]) for item in holdings.values()
        ),
        "realized_pnl": sum(
            Decimal(item["realized_pnl"]) for item in holdings.values()
        ),
    }
    totals["income"] = Decimal("20.00")
    totals["open_pnl"] = totals["market_value"] - totals["remaining_cost"]
    totals["total_pnl"] = (
        totals["open_pnl"] + totals["realized_pnl"] + totals["income"]
    )

    return {
        "holdings": holdings,
        "totals": {
            key: f"{_money(value):.2f}" for key, value in totals.items()
        },
    }


def test_portfolio_synthetic_fixture_contract_is_explicit() -> None:
    fixture = _load_fixture()
    transactions = fixture["transactions"]

    assert fixture["schema_version"] == "portfolio-synthetic-certification.v1"
    assert fixture["issue"] == 303
    assert fixture["environment"] == {
        "test_ready": True,
        "ready_for_real_data": False,
        "real_data_allowed": False,
    }
    assert {row["asset_type"] for row in transactions} == {
        "ACAO",
        "FII",
        "ETF_NACIONAL",
        "BDR",
        "CRIPTO",
        "TESOURO_DIRETO",
        "RENDA_FIXA",
    }
    assert any(row["operation"] == "sell" for row in transactions)
    assert any(Decimal(row["fees"]) > 0 for row in transactions)
    assert fixture["market_prices"]["missing_coverage"] == ["BDR-COVERAGE-GAP"]


def test_portfolio_synthetic_fixture_covers_required_cases() -> None:
    fixture = _load_fixture()
    transactions = fixture["transactions"]

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for transaction in transactions:
        grouped[transaction["ticker"]].append(transaction)

    assert sum(1 for row in grouped["PETR4"] if row["operation"] == "buy") >= 2
    assert any(row["operation"] == "sell" for row in grouped["PETR4"])
    assert grouped["BOVA11"][0]["operation"] == "buy"
    assert grouped["BOVA11"][1]["operation"] == "sell"
    assert grouped["BOVA11"][2]["operation"] == "buy"
    assert Decimal(grouped["BOVA11"][1]["quantity"]) == Decimal("20")
    assert Decimal(grouped["BOVA11"][2]["quantity"]) > 0
    income_tickers = {event["ticker"] for event in fixture["income_events"]}

    assert income_tickers == {"MXRF11"}
    assert "AAPL34" not in income_tickers


@pytest.mark.asyncio
async def test_portfolio_synthetic_fixture_is_valid_csv_contract() -> None:
    fixture = _load_fixture()

    rows, global_errors = await parse_csv_content(
        _to_csv(fixture["transactions"]),
        portfolio_id=303,
        db=AsyncSession,
    )

    assert global_errors == []
    assert len(rows) == len(fixture["transactions"])
    assert all(row.is_valid() for row in rows)
    assert all(row.warnings == [] for row in rows)


def test_portfolio_synthetic_fixture_reconciles_independently() -> None:
    fixture = _load_fixture()

    actual = _reconcile(
        fixture["transactions"],
        fixture["market_prices"]["prices"],
    )

    assert actual == fixture["expected"]
