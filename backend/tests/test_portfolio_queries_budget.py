"""Testes de orçamento de queries em leituras financeiras (OP-07 / SGI007 / SGI013)."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.query_budget import QueryBudgetExceeded, assert_max_queries


@pytest.mark.asyncio
async def test_financial_read_query_budget_enforcement() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        # 1. Leitura dentro do orçamento de 3 queries passa e captura os statements
        with assert_max_queries(engine, maximum=3) as statements:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1 AS portfolio_summary"))
                await connection.execute(text("SELECT 2 AS portfolio_positions"))

        assert len(statements) == 2
        assert "portfolio_summary" in statements[0]
        assert "portfolio_positions" in statements[1]

        # 2. Leitura que excede o orçamento contratual falha com QueryBudgetExceeded
        with pytest.raises(QueryBudgetExceeded) as exc_info:
            with assert_max_queries(engine, maximum=2):
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
                    await connection.execute(text("SELECT 2"))
                    await connection.execute(text("SELECT 3"))

        assert exc_info.value.actual == 3
        assert exc_info.value.maximum == 2
    finally:
        await engine.dispose()
