from datetime import date
from decimal import Decimal

import pytest
from fastapi import BackgroundTasks

from app.models.fixed_income import (
    FixedIncomeInvestment,
    FixedIncomeType,
    IndexerType,
)
from app.models.transaction import OperationType, Transaction
from app.routers import transactions
from app.schemas.transaction import TransactionUpdate


class _Result:
    def __init__(self, value) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _LifecycleSession:
    def __init__(self, *execute_values) -> None:
        self.execute_values = list(execute_values)
        self.added = []
        self.deleted = []
        self.commit_called = False

    async def execute(self, _statement):
        value = self.execute_values.pop(0) if self.execute_values else None
        return _Result(value)

    def add(self, value) -> None:
        self.added.append(value)

    async def delete(self, value) -> None:
        self.deleted.append(value)

    async def commit(self) -> None:
        self.commit_called = True

    async def refresh(self, _value) -> None:
        pass


async def _allow_portfolio(*_args, **_kwargs):
    return object()


async def _allow_validation(*_args, **_kwargs):
    return None


def _transaction(
    *,
    transaction_id: int,
    asset_type: str = "RENDA_FIXA",
    operation: OperationType = OperationType.buy,
) -> Transaction:
    return Transaction(
        id=transaction_id,
        portfolio_id=1,
        ticker="CDB-TESTE",
        asset_type=asset_type,
        operation=operation,
        quantity=Decimal("1"),
        price=Decimal("1000"),
        fees=Decimal("0"),
        date=date(2026, 8, 11),
        currency="BRL",
        notes="Indexador: CDI | Taxa: 110% | Emissor: Banco Teste",
    )


def _fixed_income() -> FixedIncomeInvestment:
    return FixedIncomeInvestment(
        id=50,
        portfolio_id=1,
        name="CDB-TESTE",
        institution="Banco Teste",
        fixed_income_type=FixedIncomeType.CDB,
        indexer=IndexerType.CDI,
        rate=Decimal("110"),
        invested_amount=Decimal("1000"),
        date_start=date(2026, 8, 11),
        daily_liquidity=True,
        date_maturity=None,
        is_active=True,
        is_ir_exempt=False,
    )


def _projection_was_reconciled(
    db: _LifecycleSession,
    fixed_income: FixedIncomeInvestment,
) -> bool:
    return fixed_income.is_active is False or fixed_income in db.deleted


@pytest.mark.xfail(
    strict=True,
    reason="#306: buy -> sell ainda deixa fixed_income_investments ativo",
)
@pytest.mark.asyncio
async def test_fixed_income_buy_to_sell_reconciles_previous_projection(
    monkeypatch,
) -> None:
    tx = _transaction(transaction_id=101)
    fixed_income = _fixed_income()
    db = _LifecycleSession(tx, fixed_income)

    monkeypatch.setattr(transactions, "_get_portfolio", _allow_portfolio)
    monkeypatch.setattr(
        transactions,
        "_validate_crypto_transaction_asset",
        _allow_validation,
    )
    monkeypatch.setattr(transactions, "_validate_sell", _allow_validation)

    result = await transactions.update_transaction(
        portfolio_id=1,
        transaction_id=101,
        payload=TransactionUpdate(operation="sell"),
        background_tasks=BackgroundTasks(),
        db=db,
        current_user=object(),
    )

    assert result.operation == OperationType.sell
    assert db.commit_called is True
    assert _projection_was_reconciled(db, fixed_income)


@pytest.mark.xfail(
    strict=True,
    reason="#306: mudanca de classe ainda deixa projecao RF ativa",
)
@pytest.mark.asyncio
async def test_fixed_income_change_to_non_fixed_income_reconciles_projection(
    monkeypatch,
) -> None:
    tx = _transaction(transaction_id=102)
    fixed_income = _fixed_income()
    db = _LifecycleSession(tx, fixed_income)

    monkeypatch.setattr(transactions, "_get_portfolio", _allow_portfolio)
    monkeypatch.setattr(
        transactions,
        "_validate_crypto_transaction_asset",
        _allow_validation,
    )

    result = await transactions.update_transaction(
        portfolio_id=1,
        transaction_id=102,
        payload=TransactionUpdate(asset_type="ACAO"),
        background_tasks=BackgroundTasks(),
        db=db,
        current_user=object(),
    )

    assert result.asset_type == "ACAO"
    assert db.commit_called is True
    assert _projection_was_reconciled(db, fixed_income)


@pytest.mark.xfail(
    strict=True,
    reason="#306: delete ainda remove apenas Transaction",
)
@pytest.mark.asyncio
async def test_delete_fixed_income_transaction_reconciles_projection(
    monkeypatch,
) -> None:
    tx = _transaction(transaction_id=103)
    fixed_income = _fixed_income()
    db = _LifecycleSession(tx, fixed_income)

    monkeypatch.setattr(transactions, "_get_portfolio", _allow_portfolio)

    await transactions.delete_transaction(
        portfolio_id=1,
        transaction_id=103,
        background_tasks=BackgroundTasks(),
        db=db,
        current_user=object(),
    )

    assert tx in db.deleted
    assert db.commit_called is True
    assert _projection_was_reconciled(db, fixed_income)