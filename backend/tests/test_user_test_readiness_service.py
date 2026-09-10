from __future__ import annotations

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.user_test_readiness_service import build_user_test_readiness


@pytest.mark.asyncio
async def test_user_test_readiness_is_read_only_and_goes_assisted_when_core_data_exists() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE alembic_version (version_num TEXT)"))
        await connection.execute(
            text("INSERT INTO alembic_version VALUES ('20260910_goals_runtime')")
        )
        await connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        await connection.execute(text("CREATE TABLE portfolios (id INTEGER PRIMARY KEY)"))
        await connection.execute(text("CREATE TABLE transactions (id INTEGER PRIMARY KEY)"))
        await connection.execute(text("CREATE TABLE assets (id INTEGER PRIMARY KEY)"))
        await connection.execute(
            text("CREATE TABLE asset_prices (id INTEGER PRIMARY KEY, asset_id INTEGER, timestamp TEXT)")
        )
        await connection.execute(
            text("CREATE TABLE portfolio_snapshots (id INTEGER PRIMARY KEY, portfolio_id INTEGER, snapshot_date TEXT)")
        )
        await connection.execute(text("CREATE TABLE asset_dividends (id INTEGER PRIMARY KEY)"))
        await connection.execute(text("CREATE TABLE corporate_events (id INTEGER PRIMARY KEY)"))
        await connection.execute(text("CREATE TABLE goals (id INTEGER PRIMARY KEY)"))

        for table in (
            "users",
            "portfolios",
            "transactions",
            "assets",
            "portfolio_snapshots",
            "asset_dividends",
            "corporate_events",
            "goals",
        ):
            await connection.execute(text(f'INSERT INTO "{table}" (id) VALUES (1)'))
        await connection.execute(
            text("INSERT INTO asset_prices (id, asset_id, timestamp) VALUES (1, 1, '2026-09-10')")
        )

    statements: list[str] = []

    def capture_statement(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        statements.append(statement.strip())

    event.listen(engine.sync_engine, "before_cursor_execute", capture_statement)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            report = await build_user_test_readiness(session)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture_statement)
        await engine.dispose()

    assert report.schema_version == "user-test-readiness.v1"
    assert report.go_for_assisted_user_tests is True
    assert report.ready_for_real_data is False
    assert report.status == "GO_ASSISTED"
    assert report.blockers == []
    assert report.safety["read_only"] is True
    assert report.safety["promotes_ready_for_real_data"] is False

    write_verbs = {"INSERT", "UPDATE", "DELETE", "TRUNCATE", "DROP", "ALTER", "CREATE"}
    executed_verbs = {
        statement.split(maxsplit=1)[0].upper()
        for statement in statements
        if statement
    }
    assert executed_verbs.isdisjoint(write_verbs)


@pytest.mark.asyncio
async def test_user_test_readiness_blocks_when_goals_runtime_migration_is_missing() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE alembic_version (version_num TEXT)"))
        await connection.execute(text("INSERT INTO alembic_version VALUES ('old')"))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            report = await build_user_test_readiness(session)
    finally:
        await engine.dispose()

    assert report.go_for_assisted_user_tests is False
    assert "goals_runtime_schema" in report.blockers
