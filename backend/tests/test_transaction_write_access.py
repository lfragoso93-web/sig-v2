"""Authorization boundary for canonical transaction writes."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext, PortfolioAccessDenied
from app.schemas.transaction import TransactionCreate
from app.services.transaction_write_service import (
    WRITE_PORTFOLIO_TRANSACTIONS,
    add_transaction_record,
)


def _payload() -> TransactionCreate:
    return TransactionCreate(
        ticker="PETR4",
        asset_type="ACAO",
        operation="buy",
        quantity=1,
        price=10,
        date="2026-11-02",
    )


@pytest.mark.asyncio
async def test_canonical_writer_checks_owner_before_any_write() -> None:
    db = AsyncMock(spec=AsyncSession)
    ownership_result = MagicMock()
    ownership_result.scalar_one_or_none.return_value = None
    db.execute.return_value = ownership_result
    access = PortfolioAccessContext.for_user(
        user_id=3,
        portfolio_id=7,
        permissions=frozenset({WRITE_PORTFOLIO_TRANSACTIONS}),
    )

    with pytest.raises(PortfolioAccessDenied):
        await add_transaction_record(
            db,
            portfolio_id=7,
            access=access,
            payload=_payload(),
        )

    db.execute.assert_awaited_once()
    ownership_query = str(db.execute.await_args.args[0])
    assert "portfolios.id" in ownership_query
    assert "portfolios.user_id" in ownership_query
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_canonical_writer_rejects_context_for_another_portfolio_before_query() -> None:
    db = AsyncMock(spec=AsyncSession)
    access = PortfolioAccessContext.for_system(
        portfolio_id=8,
        permissions=frozenset({WRITE_PORTFOLIO_TRANSACTIONS}),
        purpose="transaction-write-test",
    )

    with pytest.raises(PortfolioAccessDenied):
        await add_transaction_record(
            db,
            portfolio_id=7,
            access=access,
            payload=_payload(),
        )

    db.execute.assert_not_awaited()
    db.add.assert_not_called()
