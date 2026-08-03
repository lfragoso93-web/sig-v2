"""On-demand portfolio dividend projections from canonical global events."""

from __future__ import annotations

import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.models.dividend_enums import DividendType
from app.models.transaction import OperationType
from app.schemas.dividend import DividendRead
from app.services.dividend_service import (
    build_dividend_projection,
    calculate_quantity_on_date,
    list_dividends,
)

SERVICE_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "services" / "dividend_service.py"
)


def _transaction(
    operation: OperationType,
    quantity: float,
    transaction_date: date,
    ticker: str = "petr4",
) -> SimpleNamespace:
    return SimpleNamespace(
        operation=operation,
        quantity=quantity,
        date=transaction_date,
        ticker=ticker,
    )


def _event(
    *,
    record_date: date | None = date(2026, 1, 10),
    ex_date: date = date(2026, 1, 13),
    value_per_unit: Decimal = Decimal("1.25"),
) -> SimpleNamespace:
    return SimpleNamespace(
        id=91,
        record_date=record_date,
        ex_date=ex_date,
        payment_date=date(2026, 2, 1),
        value_per_unit=value_per_unit,
        dividend_type=DividendType.DIVIDENDO,
    )


def test_purchase_before_entitlement_date_generates_gross_right() -> None:
    projection = build_dividend_projection(
        _event(),
        " petr4 ",
        7,
        [_transaction(OperationType.buy, 10, date(2026, 1, 9))],
    )

    assert projection is not None
    assert projection.ticker == "PETR4"
    assert projection.total_received == pytest.approx(12.5)
    assert projection.model_dump() == {
        "ticker": "PETR4",
        "ex_date": date(2026, 1, 13),
        "payment_date": date(2026, 2, 1),
        "value_per_unit": 1.25,
        "dividend_type": "DIVIDENDO",
        "id": 91,
        "total_received": 12.5,
        "portfolio_id": 7,
    }


def test_purchase_after_entitlement_date_does_not_generate_right() -> None:
    projection = build_dividend_projection(
        _event(),
        "PETR4",
        7,
        [_transaction(OperationType.buy, 10, date(2026, 1, 11))],
    )

    assert projection is None


def test_sale_before_entitlement_date_reduces_eligible_quantity() -> None:
    quantity = calculate_quantity_on_date(
        [
            _transaction(OperationType.buy, 10, date(2026, 1, 2)),
            _transaction(OperationType.sell, 4, date(2026, 1, 9)),
        ],
        date(2026, 1, 10),
    )

    assert quantity == Decimal(6)


def test_fully_sold_position_and_negative_position_do_not_project() -> None:
    transactions = [
        _transaction(OperationType.buy, 10, date(2026, 1, 2)),
        _transaction(OperationType.sell, 12, date(2026, 1, 9)),
    ]

    assert calculate_quantity_on_date(transactions, date(2026, 1, 10)) == 0
    assert build_dividend_projection(_event(), "PETR4", 7, transactions) is None


def test_record_date_has_priority_over_ex_date() -> None:
    projection = build_dividend_projection(
        _event(record_date=date(2026, 1, 10), ex_date=date(2026, 1, 13)),
        "PETR4",
        7,
        [_transaction(OperationType.buy, 10, date(2026, 1, 11))],
    )

    assert projection is None


def test_ex_date_is_explicit_fallback_when_record_date_is_missing() -> None:
    projection = build_dividend_projection(
        _event(record_date=None, ex_date=date(2026, 1, 13)),
        "PETR4",
        7,
        [_transaction(OperationType.buy, 10, date(2026, 1, 11))],
    )

    assert projection is not None
    assert isinstance(projection, DividendRead)


@pytest.mark.asyncio
async def test_list_dividends_queries_canonical_data_and_preserves_order() -> None:
    db = AsyncMock()
    ownership_result = Mock()
    ownership_result.scalar_one_or_none.return_value = SimpleNamespace(id=7)
    event_result = Mock()
    newer_event = _event(ex_date=date(2026, 3, 1))
    older_event = _event(ex_date=date(2026, 2, 1))
    event_result.all.return_value = [
        (newer_event, "petr4"),
        (older_event, "PETR4"),
    ]
    transaction_result = Mock()
    transaction_result.scalars.return_value.all.return_value = [
        _transaction(OperationType.buy, 10, date(2026, 1, 1))
    ]
    db.execute.side_effect = [
        ownership_result,
        event_result,
        transaction_result,
    ]

    projections = await list_dividends(db, portfolio_id=7, user_id=3)

    assert [projection.ex_date for projection in projections] == [
        date(2026, 3, 1),
        date(2026, 2, 1),
    ]
    assert all(isinstance(projection, DividendRead) for projection in projections)
    assert db.execute.await_count == 3


def test_service_neither_depends_on_legacy_dividend_nor_writes() -> None:
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert "app.models.dividend" not in imported_modules
    assert "Dividend" not in imported_names
    assert {"commit", "flush", "delete"}.isdisjoint(called_attributes)
