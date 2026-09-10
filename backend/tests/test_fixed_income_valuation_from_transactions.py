from datetime import date
from decimal import Decimal

import pytest

from app.models.transaction import OperationType, Transaction
from app.services.fixed_income_valuation_service import (
    get_fixed_income_totals_from_transactions,
)


class _NoExecuteSession:
    async def execute(self, *_args, **_kwargs):
        raise AssertionError("preloaded fixed-income transactions should not be reloaded")


@pytest.mark.asyncio
async def test_fixed_income_totals_from_transactions_reuses_preloaded_rows():
    transactions = [
        Transaction(
            id=1,
            portfolio_id=7,
            ticker="CDB-TESTE",
            asset_type="RENDA_FIXA",
            operation=OperationType.buy,
            quantity=Decimal("1"),
            price=Decimal("1000"),
            fees=Decimal("0"),
            date=date(2026, 1, 2),
            currency="BRL",
            notes="Indexador: PREFIXADO | Taxa: 12%",
        )
    ]

    totals = await get_fixed_income_totals_from_transactions(
        _NoExecuteSession(),
        transactions,
        date(2026, 1, 12),
    )

    assert totals["invested_amount"] == Decimal("1000.00")
    assert totals["current_value"] > Decimal("1000.00")
    assert totals["income_amount"] > Decimal("0.00")
