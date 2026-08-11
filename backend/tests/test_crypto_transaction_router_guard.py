from __future__ import annotations

import ast
import inspect
import textwrap

import pytest
from fastapi import HTTPException

from app.routers import transactions
from app.services.crypto_transaction_eligibility_service import (
    CryptoTransactionEligibilityError,
)


def _top_level_call_index(function, call_name: str) -> int:
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    body = tree.body[0].body
    for index, statement in enumerate(body):
        for node in ast.walk(statement):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == call_name:
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
        if isinstance(statement.value, ast.Call) and isinstance(statement.value.func, ast.Name):
            if statement.value.func.id == "Transaction":
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
