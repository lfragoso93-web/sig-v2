"""Regressões de isolamento por usuário e carteira no router IRPF."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers.irpf import _get_portfolio


class _Result:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Db:
    def __init__(self, value):
        self._value = value
        self.calls = 0

    async def execute(self, statement):
        self.calls += 1
        self.statement = statement
        return _Result(self._value)


@pytest.mark.asyncio
async def test_get_portfolio_returns_owned_portfolio() -> None:
    portfolio = SimpleNamespace(id=7, user_id=3)
    db = _Db(portfolio)

    result = await _get_portfolio(
        portfolio_id=7,
        user=SimpleNamespace(id=3),
        db=db,
    )

    assert result is portfolio
    assert db.calls == 1


@pytest.mark.asyncio
async def test_get_portfolio_hides_foreign_or_missing_portfolio() -> None:
    db = _Db(None)

    with pytest.raises(HTTPException) as exc_info:
        await _get_portfolio(
            portfolio_id=7,
            user=SimpleNamespace(id=99),
            db=db,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Carteira nao encontrada."
