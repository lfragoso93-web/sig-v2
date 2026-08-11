from __future__ import annotations

import ast
import inspect
import textwrap
from datetime import date

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.models.transaction import OperationType, Transaction
from app.routers import transactions
from app.schemas.transaction import TransactionCreate
from app.services.crypto_transaction_eligibility_service import (
    CryptoTransactionEligibilityError,
)


def _top_level_call_index(function, call_name: str) -> int:
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    body = tree.body[0].body
    for index, statement in enumerate(body):
        for node in ast.walk(statement):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == call_name
            ):
                return index
    raise AssertionError(f"call not found: {call_name}")


def _transaction_assignment_index(function) -> int:
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    body = tree.body[0].body
    for index, statement in enumerate(body):
        if not isinstance(statement, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "tx"
            for target in statement.targets
        ):
            continue
        if (
            isinstance(statement.value, ast.Call)
            and isinstance(statement.value.func, ast.Name)
            and statement.value.func.id == "Transaction"
        ):
            return index
    raise AssertionError("Transaction assignment not found")


def _transaction_mutation_index(function) -> int:
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    body = tree.body[0].body
    for index, statement in enumerate(body):
        if not isinstance(statement, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "tx"
            for target in statement.targets
        ):
            return index
    raise AssertionError("transaction mutation not found")


class _Result:
    def __init__(self, value) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _WriteSpySession:
    def __init__(self, execute_value=None) -> None:
        self.execute_value = execute_value
        self.add_called = False
        self.commit_called = False

    async def execute(self, _statement):
        return _Result(self.execute_value)

    def add(self, _value) -> None:
        self.add_called = True

    async def commit(self) -> None:
        self.commit_called = True

    async def refresh(self, _value) -> None:
        pass


def _payload(ticker: str) -> TransactionCreate:
    return TransactionCreate(
        ticker=ticker,
        asset_type="CRIPTO",
        operation="buy",
        quantity=1,
        price=100,
        fees=0,
        date=date(2026, 8, 11),
        currency="BRL",
    )


async def _allow_portfolio(*_args, **_kwargs):
    return object()


async def _reject_crypto(_db, ticker, _asset_type):
    raise HTTPException(
        status_code=422,
        detail=f"CRIPTO {ticker} não elegível para transações",
    )


def test_create_crypto_guard_runs_before_transaction_construction() -> None:
    guard_index = _top_level_call_index(
        transactions.create_transaction,
        "_validate_crypto_transaction_asset",
    )
    transaction_index = _transaction_assignment_index(transactions.create_transaction)

    assert guard_index < transaction_index


def test_update_crypto_guard_runs_before_transaction_mutation() -> None:
    guard_index = _top_level_call_index(
        transactions.update_transaction,
        "_validate_crypto_transaction_asset",
    )
    mutation_index = _transaction_mutation_index(transactions.update_transaction)

    assert guard_index < mutation_index


def test_crypto_requests_do_not_use_get_or_create_asset_after_commit() -> None:
    source = textwrap.dedent(inspect.getsource(transactions.create_transaction))

    assert 'if asset_type != "CRIPTO":' in source
    assert "await get_or_create_asset(db, asset_data)" in source


@pytest.mark.asyncio
async def test_non_crypto_transaction_skips_crypto_eligibility(monkeypatch) -> None:
    called = False

    async def _unexpected_call(_db, _ticker):
        nonlocal called
        called = True

    monkeypatch.setattr(
        transactions,
        "require_financially_certified_crypto_asset",
        _unexpected_call,
    )

    await transactions._validate_crypto_transaction_asset(object(), "PETR4", "ACAO")

    assert called is False


@pytest.mark.asyncio
async def test_rejected_crypto_is_exposed_as_unprocessable_entity(monkeypatch) -> None:
    async def _reject(_db, ticker):
        raise CryptoTransactionEligibilityError(
            ticker=ticker,
            reason="histórico financeiro não certificado",
            provider_status="HISTORY_START_COMPLEMENT_GAPPED",
        )

    monkeypatch.setattr(
        transactions,
        "require_financially_certified_crypto_asset",
        _reject,
    )

    with pytest.raises(HTTPException) as exc_info:
        await transactions._validate_crypto_transaction_asset(object(), "APT", "CRIPTO")

    assert exc_info.value.status_code == 422
    assert "APT" in str(exc_info.value.detail)
    assert "HISTORY_START_COMPLEMENT_GAPPED" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_rejected_create_does_not_add_or_commit(monkeypatch) -> None:
    db = _WriteSpySession()
    monkeypatch.setattr(transactions, "_get_portfolio", _allow_portfolio)
    monkeypatch.setattr(transactions, "_validate_crypto_transaction_asset", _reject_crypto)

    with pytest.raises(HTTPException) as exc_info:
        await transactions.create_transaction(
            portfolio_id=1,
            payload=_payload("APT"),
            background_tasks=BackgroundTasks(),
            db=db,
            current_user=object(),
        )

    assert exc_info.value.status_code == 422
    assert db.add_called is False
    assert db.commit_called is False


@pytest.mark.asyncio
async def test_rejected_update_does_not_mutate_or_commit(monkeypatch) -> None:
    existing = Transaction(
        id=10,
        portfolio_id=1,
        ticker="BTC",
        asset_type="CRIPTO",
        operation=OperationType.buy,
        quantity=1,
        price=100,
        fees=0,
        date=date(2026, 8, 10),
        currency="BRL",
    )
    db = _WriteSpySession(existing)
    monkeypatch.setattr(transactions, "_get_portfolio", _allow_portfolio)
    monkeypatch.setattr(transactions, "_validate_crypto_transaction_asset", _reject_crypto)

    with pytest.raises(HTTPException) as exc_info:
        await transactions.update_transaction(
            portfolio_id=1,
            transaction_id=10,
            payload=_payload("APT"),
            background_tasks=BackgroundTasks(),
            db=db,
            current_user=object(),
        )

    assert exc_info.value.status_code == 422
    assert existing.ticker == "BTC"
    assert existing.asset_type == "CRIPTO"
    assert db.commit_called is False


def test_transaction_eligibility_service_has_no_provider_imports() -> None:
    module = __import__(
        "app.services.crypto_transaction_eligibility_service",
        fromlist=["*"],
    )
    tree = ast.parse(inspect.getsource(module))
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert not any("coingecko" in module_name.lower() for module_name in imported_modules)
    assert not any("brapi" in module_name.lower() for module_name in imported_modules)
    assert not any("httpx" in module_name.lower() for module_name in imported_modules)
