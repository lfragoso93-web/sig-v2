from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.transaction import OperationType, Transaction
from app.services.csv_import_service import import_transactions_csv


class _Upload:
    def __init__(self, content: str):
        self._content = content.encode("utf-8")

    async def read(self) -> bytes:
        return self._content


async def _ticker_count(db, portfolio_id: int, ticker: str) -> int:
    result = await db.execute(
        select(func.count(Transaction.id)).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.ticker == ticker,
        )
    )
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_existing_duplicate_blocks_mixed_batch_in_dry_run_and_import(db, portfolio):
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker="PETR4",
            asset_type="ACAO",
            operation=OperationType.buy,
            quantity=1,
            price=10,
            fees=0,
            date=date(2026, 1, 2),
            currency="BRL",
        )
    )
    await db.flush()

    content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,1,10,2026-01-02,0,BRL,duplicada
VALE3,ACAO,buy,2,20,2026-01-03,0,BRL,nova"""

    dry_run = await import_transactions_csv(
        db=db,
        portfolio_id=portfolio.id,
        user_id=portfolio.user_id,
        file=_Upload(content),
        dry_run=True,
    )

    assert dry_run["success"] is False
    assert dry_run["imported_count"] == 0
    assert dry_run["error_count"] == 1
    assert dry_run["rows"][0]["errors"] == ["duplicate transaction already exists"]
    assert dry_run["rows"][1]["status"] == "valid"

    imported = await import_transactions_csv(
        db=db,
        portfolio_id=portfolio.id,
        user_id=portfolio.user_id,
        file=_Upload(content),
        dry_run=False,
    )

    assert imported["success"] is False
    assert imported["imported_count"] == 0
    assert imported["error_count"] == 1
    assert await _ticker_count(db, portfolio.id, "VALE3") == 0


@pytest.mark.asyncio
async def test_duplicate_rows_inside_csv_block_entire_batch_before_persistence(db, portfolio):
    content = """ticker,asset_type,operation,quantity,price,date,fees,currency,notes
PETR4,ACAO,buy,1,10,2026-01-02,0,BRL,primeira
PETR4,ACAO,buy,1,10,2026-01-02,0,BRL,repetida"""

    dry_run = await import_transactions_csv(
        db=db,
        portfolio_id=portfolio.id,
        user_id=portfolio.user_id,
        file=_Upload(content),
        dry_run=True,
    )

    assert dry_run["success"] is False
    assert dry_run["imported_count"] == 0
    assert dry_run["error_count"] == 1
    assert dry_run["rows"][1]["errors"] == ["duplicate transaction in CSV"]

    imported = await import_transactions_csv(
        db=db,
        portfolio_id=portfolio.id,
        user_id=portfolio.user_id,
        file=_Upload(content),
        dry_run=False,
    )

    assert imported["success"] is False
    assert imported["imported_count"] == 0
    assert imported["error_count"] == 1
    assert await _ticker_count(db, portfolio.id, "PETR4") == 0
