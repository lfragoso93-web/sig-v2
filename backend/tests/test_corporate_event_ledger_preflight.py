from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.transaction import OperationType, Transaction
from app.services.corporate_event_ledger_preflight import (
    read_ledger_transaction_preflight,
)


@pytest.mark.asyncio
async def test_ledger_preflight_is_read_only_and_aggregates_transactions(
    db, portfolio
) -> None:
    db.add_all(
        [
            Transaction(
                portfolio_id=portfolio.id,
                ticker="amob3",
                asset_type="ACAO",
                operation=OperationType.buy,
                quantity=Decimal("100"),
                price=Decimal("0.35"),
                date=date(2024, 1, 10),
                currency="BRL",
            ),
            Transaction(
                portfolio_id=portfolio.id,
                ticker="AMOB3",
                asset_type="ACAO",
                operation=OperationType.buy,
                quantity=Decimal("200"),
                price=Decimal("0.26"),
                date=date(2024, 2, 10),
                currency="BRL",
            ),
            Transaction(
                portfolio_id=portfolio.id,
                ticker="AMOB3",
                asset_type="ACAO",
                operation=OperationType.sell,
                quantity=Decimal("6"),
                price=Decimal("13.80"),
                date=date(2025, 1, 10),
                currency="BRL",
            ),
        ]
    )
    await db.flush()
    before = await db.scalar(select(func.count()).select_from(Transaction))

    snapshot = await read_ledger_transaction_preflight(
        db,
        portfolio_id=portfolio.id,
        ticker=" amob3 ",
        as_of=date(2025, 1, 10),
    )

    after = await db.scalar(select(func.count()).select_from(Transaction))
    assert snapshot.transaction_count == 3
    assert snapshot.buy_quantity == Decimal("300")
    assert snapshot.sell_quantity == Decimal("6")
    assert snapshot.net_quantity == Decimal("294")
    assert snapshot.first_transaction_date == date(2024, 1, 10)
    assert snapshot.last_transaction_date == date(2025, 1, 10)
    assert before == after == 3


@pytest.mark.asyncio
async def test_ledger_preflight_excludes_future_transactions(db, portfolio) -> None:
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker="AMOB3",
            asset_type="ACAO",
            operation=OperationType.buy,
            quantity=Decimal("10"),
            price=Decimal("1"),
            date=date(2026, 1, 1),
            currency="BRL",
        )
    )
    await db.flush()

    snapshot = await read_ledger_transaction_preflight(
        db,
        portfolio_id=portfolio.id,
        ticker="AMOB3",
        as_of=date(2025, 12, 31),
    )

    assert snapshot.transaction_ids == ()
    assert snapshot.net_quantity == Decimal("0")


@pytest.mark.asyncio
async def test_ledger_preflight_requires_ticker(db, portfolio) -> None:
    with pytest.raises(ValueError, match="ticker e obrigatorio"):
        await read_ledger_transaction_preflight(
            db,
            portfolio_id=portfolio.id,
            ticker=" ",
            as_of=date(2025, 1, 1),
        )
