"""Equivalência contábil entre o IRPF legado e as baixas canônicas.

Este módulo não altera regras fiscais. Ele congela somente cenários Swing Trade
simples em que a reconstrução atual do IRPF deve reconciliar com a projeção
canônica de realizações antes da migração do consumidor de produção.
"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from app.models.transaction import OperationType
from app.services.irpf_tax_service import calc_ganhos_capital
from app.services.snapshot_position_projection import project_transaction_timelines

from tests.irpf_characterization_helpers import db_with_transactions, transaction


def _canonical_transaction(
    *,
    ticker: str,
    operation: OperationType,
    quantity: str,
    price: str,
    tx_date: date,
    fees: str = "0",
    transaction_id: int,
):
    return SimpleNamespace(
        id=transaction_id,
        ticker=ticker,
        operation=operation,
        asset_type="ETF",
        quantity=Decimal(quantity),
        price=Decimal(price),
        date=tx_date,
        currency="BRL",
        fees=Decimal(fees),
        fx_rate=None,
    )


def _canonical_disposals(transactions: list) -> tuple:
    projected = project_transaction_timelines(
        transactions=transactions,
        actions_by_ticker={},
        target_date=date(2024, 12, 31),
    )
    return tuple(
        disposal
        for projection, _, _ in projected.values()
        for disposal in projection.realized_disposals
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("legacy_transactions", "canonical_transactions", "expected_pnl"),
    [
        (
            [
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity=10,
                    price=10,
                    tx_date=date(2024, 1, 2),
                ),
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity=10,
                    price=12,
                    tx_date=date(2024, 2, 2),
                ),
            ],
            [
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity="10",
                    price="10",
                    tx_date=date(2024, 1, 2),
                    transaction_id=1,
                ),
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity="10",
                    price="12",
                    tx_date=date(2024, 2, 2),
                    transaction_id=2,
                ),
            ],
            Decimal(20),
        ),
        (
            [
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity=20,
                    price=10,
                    tx_date=date(2024, 1, 2),
                ),
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity=5,
                    price=14,
                    tx_date=date(2024, 2, 2),
                ),
            ],
            [
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity="20",
                    price="10",
                    tx_date=date(2024, 1, 2),
                    transaction_id=1,
                ),
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity="5",
                    price="14",
                    tx_date=date(2024, 2, 2),
                    transaction_id=2,
                ),
            ],
            Decimal(20),
        ),
        (
            [
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity=10,
                    price=10,
                    tx_date=date(2024, 1, 2),
                ),
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity=10,
                    price=20,
                    tx_date=date(2024, 1, 3),
                ),
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity=10,
                    price=18,
                    tx_date=date(2024, 2, 2),
                ),
            ],
            [
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity="10",
                    price="10",
                    tx_date=date(2024, 1, 2),
                    transaction_id=1,
                ),
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity="10",
                    price="20",
                    tx_date=date(2024, 1, 3),
                    transaction_id=2,
                ),
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity="10",
                    price="18",
                    tx_date=date(2024, 2, 2),
                    transaction_id=3,
                ),
            ],
            Decimal(30),
        ),
        (
            [
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity=10,
                    price=10,
                    tx_date=date(2024, 1, 2),
                ),
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity=10,
                    price=12,
                    tx_date=date(2024, 2, 2),
                ),
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity=5,
                    price=20,
                    tx_date=date(2024, 3, 2),
                ),
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity=5,
                    price=21,
                    tx_date=date(2024, 4, 2),
                ),
            ],
            [
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity="10",
                    price="10",
                    tx_date=date(2024, 1, 2),
                    transaction_id=1,
                ),
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity="10",
                    price="12",
                    tx_date=date(2024, 2, 2),
                    transaction_id=2,
                ),
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity="5",
                    price="20",
                    tx_date=date(2024, 3, 2),
                    transaction_id=3,
                ),
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity="5",
                    price="21",
                    tx_date=date(2024, 4, 2),
                    transaction_id=4,
                ),
            ],
            Decimal(25),
        ),
        (
            [
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity=10,
                    price=10,
                    fees=2,
                    tx_date=date(2024, 1, 2),
                ),
                transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity=10,
                    price=12,
                    fees=3,
                    tx_date=date(2024, 2, 2),
                ),
            ],
            [
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.buy,
                    quantity="10",
                    price="10",
                    fees="2",
                    tx_date=date(2024, 1, 2),
                    transaction_id=1,
                ),
                _canonical_transaction(
                    ticker="BOVA11",
                    operation=OperationType.sell,
                    quantity="10",
                    price="12",
                    fees="3",
                    tx_date=date(2024, 2, 2),
                    transaction_id=2,
                ),
            ],
            Decimal(15),
        ),
    ],
)
async def test_simple_swing_trade_accounting_matches_canonical_disposals(
    legacy_transactions: list,
    canonical_transactions: list,
    expected_pnl: Decimal,
) -> None:
    legacy_months = await calc_ganhos_capital(
        db_with_transactions(current_year=legacy_transactions),
        1,
        2024,
    )
    canonical = _canonical_disposals(canonical_transactions)

    legacy_total = Decimal(str(sum(month.lucro_swing_trade for month in legacy_months)))
    canonical_total = sum(
        (disposal.realized_pnl_brl for disposal in canonical),
        start=Decimal(0),
    )

    assert legacy_total == expected_pnl
    assert canonical_total == expected_pnl
    assert legacy_total == canonical_total


@pytest.mark.asyncio
async def test_sale_above_position_exposes_the_expected_migration_difference() -> None:
    legacy_transactions = [
        transaction(
            ticker="BOVA11",
            operation=OperationType.buy,
            quantity=10,
            price=10,
            tx_date=date(2024, 1, 2),
        ),
        transaction(
            ticker="BOVA11",
            operation=OperationType.sell,
            quantity=15,
            price=20,
            tx_date=date(2024, 2, 2),
        ),
    ]
    canonical_transactions = [
        _canonical_transaction(
            ticker="BOVA11",
            operation=OperationType.buy,
            quantity="10",
            price="10",
            tx_date=date(2024, 1, 2),
            transaction_id=1,
        ),
        _canonical_transaction(
            ticker="BOVA11",
            operation=OperationType.sell,
            quantity="15",
            price="20",
            tx_date=date(2024, 2, 2),
            transaction_id=2,
        ),
    ]

    legacy_month = (
        await calc_ganhos_capital(
            db_with_transactions(current_year=legacy_transactions),
            1,
            2024,
        )
    )[0]
    disposal = _canonical_disposals(canonical_transactions)[0]

    assert Decimal(str(legacy_month.lucro_swing_trade)) == Decimal(150)
    assert disposal.quantity_requested == Decimal(15)
    assert disposal.quantity_disposed == Decimal(10)
    assert disposal.realized_pnl_brl == Decimal(100)

    assert Decimal(str(legacy_month.lucro_swing_trade)) != disposal.realized_pnl_brl
