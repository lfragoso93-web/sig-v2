from __future__ import annotations

import ast
import inspect
import textwrap
from datetime import date

import pytest
from app.models.transaction import OperationType, Transaction
from app.routers import transactions
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.crypto_transaction_eligibility_service import (
    CryptoTransactionEligibilityError,
)
from fastapi import BackgroundTasks, HTTPException


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
        self.added = []
        self.add_called = False
        self.commit_called = False

    async def execute(self, _statement):
        return _Result(self.execute_value)

    def add(self, value) -> None:
        self.added.append(value)
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


async def _allow_crypto(*_args, **_kwargs):
    return None


async def _noop_asset(*_args, **_kwargs):
    return None


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
async def test_fixed_income_upsert_failure_blocks_transaction_commit(monkeypatch) -> None:
    async def _fail_upsert(*_args, **_kwargs):
        raise RuntimeError("fixed income upsert failed")

    db = _WriteSpySession()
    monkeypatch.setattr(transactions, "_get_portfolio", _allow_portfolio)
    monkeypatch.setattr(transactions, "_upsert_fixed_income_record", _fail_upsert)

    with pytest.raises(RuntimeError, match="fixed income upsert failed"):
        await transactions.create_transaction(
            portfolio_id=1,
            payload=TransactionCreate(
                ticker="CDB-TESTE",
                asset_type="RENDA_FIXA",
                operation="buy",
                quantity=1,
                price=1000,
                fees=0,
                date=date(2026, 8, 11),
                currency="BRL",
                notes="Indexador: CDI | Taxa: 110% | Emissor: Banco Teste",
            ),
            background_tasks=BackgroundTasks(),
            db=db,
            current_user=object(),
        )

    assert db.commit_called is False


@pytest.mark.asyncio
async def test_fixed_income_buy_prepares_record_before_commit(monkeypatch) -> None:
    db = _WriteSpySession(execute_value=None)
    monkeypatch.setattr(transactions, "_get_portfolio", _allow_portfolio)
    monkeypatch.setattr(transactions, "get_or_create_asset", _noop_asset)

    result = await transactions.create_transaction(
        portfolio_id=1,
        payload=TransactionCreate(
            ticker="CDB-TESTE",
            asset_type="RENDA_FIXA",
            operation="buy",
            quantity=1,
            price=1000,
            fees=0,
            date=date(2026, 8, 11),
            currency="BRL",
            notes="Indexador: CDI | Taxa: 110% | Emissor: Banco Teste",
        ),
        background_tasks=BackgroundTasks(),
        db=db,
        current_user=object(),
    )

    assert result.ticker == "CDB-TESTE"
    assert db.commit_called is True
    assert any(
        getattr(item, "name", None) == "CDB-TESTE"
        and getattr(item, "invested_amount", None) == transactions.Decimal("1000.0")
        for item in db.added
    )


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
            payload=TransactionUpdate(ticker="APT"),
            background_tasks=BackgroundTasks(),
            db=db,
            current_user=object(),
        )

    assert exc_info.value.status_code == 422
    assert existing.ticker == "BTC"
    assert existing.asset_type == "CRIPTO"
    assert db.commit_called is False


@pytest.mark.asyncio
async def test_partial_update_preserves_omitted_fields(monkeypatch) -> None:
    existing = Transaction(
        id=11,
        portfolio_id=1,
        ticker="BTC",
        asset_type="CRIPTO",
        operation=OperationType.buy,
        quantity=1,
        price=100,
        fees=2,
        date=date(2026, 8, 10),
        currency="BRL",
        notes="original",
    )
    db = _WriteSpySession(existing)
    monkeypatch.setattr(transactions, "_get_portfolio", _allow_portfolio)
    monkeypatch.setattr(transactions, "_validate_crypto_transaction_asset", _allow_crypto)

    result = await transactions.update_transaction(
        portfolio_id=1,
        transaction_id=11,
        payload=TransactionUpdate(price=110),
        background_tasks=BackgroundTasks(),
        db=db,
        current_user=object(),
    )

    assert result.price == 110
    assert result.ticker == "BTC"
    assert result.asset_type == "CRIPTO"
    assert result.quantity == 1
    assert result.fees == 2
    assert result.notes == "original"
    assert db.commit_called is True


@pytest.mark.asyncio
async def test_partial_update_can_clear_notes(monkeypatch) -> None:
    existing = Transaction(
        id=12,
        portfolio_id=1,
        ticker="BTC",
        asset_type="CRIPTO",
        operation=OperationType.buy,
        quantity=1,
        price=100,
        fees=0,
        date=date(2026, 8, 10),
        currency="BRL",
        notes="original",
    )
    db = _WriteSpySession(existing)
    monkeypatch.setattr(transactions, "_get_portfolio", _allow_portfolio)
    monkeypatch.setattr(transactions, "_validate_crypto_transaction_asset", _allow_crypto)

    result = await transactions.update_transaction(
        portfolio_id=1,
        transaction_id=12,
        payload=TransactionUpdate(notes=None),
        background_tasks=BackgroundTasks(),
        db=db,
        current_user=object(),
    )

    assert result.notes is None
    assert db.commit_called is True


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
