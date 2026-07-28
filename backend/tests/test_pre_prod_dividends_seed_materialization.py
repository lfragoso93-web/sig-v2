from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.transaction import OperationType
from app.services.pre_prod_dividends_seed_materialization import (
    DividendsSeedMaterializationError,
    materialize_portfolio_dividends_strict,
)


def _result(*, rows=None, scalars=None):
    result = Mock()
    result.all.return_value = rows or []
    result.scalars.return_value.all.return_value = scalars or []
    return result


def _event(
    *,
    event_id: int = 11,
    event_type: DividendType = DividendType.DIVIDENDO,
    value: Decimal = Decimal("1.25"),
) -> AssetDividend:
    return AssetDividend(
        id=event_id,
        asset_id=7,
        record_date=date(2026, 7, 24),
        ex_date=date(2026, 7, 27),
        payment_date=date(2026, 8, 10),
        value_per_unit=value,
        dividend_type=event_type,
        source="brapi",
    )


def _db(*, events=None, transactions=None, existing=None):
    return SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _result(rows=events or []),
                _result(rows=transactions or []),
                _result(scalars=existing or []),
            ]
        ),
        add=Mock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        delete=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_creates_eligible_right_without_committing() -> None:
    asset = SimpleNamespace(id=7, ticker="petr4")
    event = _event()
    db = _db(
        events=[(asset, event)],
        transactions=[
            (3, "PETR4", date(2026, 7, 1), OperationType.buy, 10),
            (3, "petr4", date(2026, 7, 20), OperationType.sell, 2),
        ],
    )

    result = await materialize_portfolio_dividends_strict(
        db=db,
        as_of=date(2026, 7, 28),
    )

    assert result.created == 1
    assert result.updated == 0
    assert result.unchanged == 0
    assert result.processed == 1
    created = db.add.call_args.args[0]
    assert isinstance(created, Dividend)
    assert created.portfolio_id == 3
    assert created.asset_dividend_id == 11
    assert created.quantity == Decimal("8.0")
    assert created.total_value == Decimal("10.000")
    assert created.net_value == Decimal("10.0")
    assert created.status == DividendStatus.A_RECEBER
    assert created.date_ex == event.ex_date
    assert created.quantity_on_date == created.quantity
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()
    db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_updates_existing_right_and_applies_jcp_net_value() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4")
    event = _event(event_type=DividendType.JCP, value=Decimal(2))
    right = Dividend(
        portfolio_id=3,
        asset_dividend_id=11,
        quantity=Decimal(1),
        total_value=Decimal(2),
        net_value=Decimal("1.70"),
        status=DividendStatus.A_RECEBER,
        ticker="PETR4",
    )
    db = _db(
        events=[(asset, event)],
        transactions=[(3, "PETR4", date(2026, 7, 1), OperationType.buy, 10)],
        existing=[right],
    )

    result = await materialize_portfolio_dividends_strict(
        db=db,
        as_of=date(2026, 8, 11),
    )

    assert result.updated == 1
    assert right.quantity == Decimal("10.0")
    assert right.total_value == Decimal("20.0")
    assert right.net_value == Decimal("17.0")
    assert right.status == DividendStatus.RECEBIDO
    assert right.dividend_type == DividendType.JCP.value
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_unchanged_right_does_not_flush() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4")
    event = _event()
    right = Dividend(
        portfolio_id=3,
        asset_dividend_id=11,
        quantity=Decimal("10.0"),
        total_value=Decimal("12.500"),
        net_value=Decimal("12.5"),
        status=DividendStatus.A_RECEBER,
        ticker="PETR4",
        ex_date=event.ex_date,
        payment_date=event.payment_date,
        value_per_unit=event.value_per_unit,
        total_received=Decimal("12.500"),
        dividend_type=DividendType.DIVIDENDO.value,
        date_ex=event.ex_date,
        date_pagamento=event.payment_date,
        quantity_on_date=Decimal("10.0"),
        value_per_share=event.value_per_unit,
    )
    db = _db(
        events=[(asset, event)],
        transactions=[(3, "PETR4", date(2026, 7, 1), OperationType.buy, 10)],
        existing=[right],
    )

    result = await materialize_portfolio_dividends_strict(
        db=db,
        as_of=date(2026, 7, 28),
    )

    assert result.unchanged == 1
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_skips_non_cash_events_without_querying_existing_rights() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4")
    db = _db(events=[(asset, _event(event_type=DividendType.BONIFICACAO))])

    result = await materialize_portfolio_dividends_strict(
        db=db,
        as_of=date(2026, 7, 28),
    )

    assert result.skipped_non_cash == 1
    assert result.processed == 0
    assert db.execute.await_count == 1
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_rejects_duplicate_existing_rights() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4")
    event = _event()
    rights = [
        Dividend(portfolio_id=3, asset_dividend_id=11),
        Dividend(portfolio_id=3, asset_dividend_id=11),
    ]
    db = _db(
        events=[(asset, event)],
        transactions=[(3, "PETR4", date(2026, 7, 1), OperationType.buy, 10)],
        existing=rights,
    )

    with pytest.raises(DividendsSeedMaterializationError, match="duplicado"):
        await materialize_portfolio_dividends_strict(
            db=db,
            as_of=date(2026, 7, 28),
        )

    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_existing_right_without_entitlement() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4")
    event = _event()
    right = Dividend(portfolio_id=3, asset_dividend_id=11)
    db = _db(
        events=[(asset, event)],
        transactions=[
            (3, "PETR4", date(2026, 7, 1), OperationType.buy, 10),
            (3, "PETR4", date(2026, 7, 20), OperationType.sell, 10),
        ],
        existing=[right],
    )

    with pytest.raises(
        DividendsSeedMaterializationError,
        match="sem elegibilidade",
    ):
        await materialize_portfolio_dividends_strict(
            db=db,
            as_of=date(2026, 7, 28),
        )

    db.delete.assert_not_awaited()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_rejects_non_positive_cash_value() -> None:
    asset = SimpleNamespace(id=7, ticker="PETR4")
    db = _db(events=[(asset, _event(value=Decimal(0)))])

    with pytest.raises(DividendsSeedMaterializationError, match="positivo"):
        await materialize_portfolio_dividends_strict(
            db=db,
            as_of=date(2026, 7, 28),
        )

    assert db.execute.await_count == 1
    db.add.assert_not_called()
