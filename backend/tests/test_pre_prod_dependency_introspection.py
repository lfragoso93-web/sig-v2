from __future__ import annotations

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.pre_prod_dependency_introspection import (
    discover_table_dependencies,
)


_WRITE_VERBS = {"INSERT", "UPDATE", "DELETE", "TRUNCATE", "DROP", "ALTER", "CREATE"}


@pytest.mark.asyncio
async def test_discovers_sqlite_foreign_keys_without_writes() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.execute(text("PRAGMA foreign_keys = ON"))
        await connection.execute(text("CREATE TABLE assets (id INTEGER PRIMARY KEY)"))
        await connection.execute(
            text(
                "CREATE TABLE asset_prices ("
                "id INTEGER PRIMARY KEY, "
                "asset_id INTEGER REFERENCES assets(id)"
                ")"
            )
        )
        await connection.execute(
            text(
                "CREATE TABLE portfolio_positions ("
                "id INTEGER PRIMARY KEY, "
                "asset_id INTEGER REFERENCES assets(id)"
                ")"
            )
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
            dependencies = await discover_table_dependencies(
                session,
                tables=["assets", "asset_prices", "portfolio_positions"],
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture_statement)
        await engine.dispose()

    assert [
        (edge.dependent, edge.dependency)
        for edge in dependencies
    ] == [
        ("asset_prices", "assets"),
        ("portfolio_positions", "assets"),
    ]
    assert all(edge.constraint_name for edge in dependencies)

    executed_verbs = {
        statement.split(maxsplit=1)[0].upper()
        for statement in statements
        if statement
    }
    assert executed_verbs.isdisjoint(_WRITE_VERBS)


@pytest.mark.asyncio
async def test_self_referential_foreign_key_is_preserved() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.execute(text("PRAGMA foreign_keys = ON"))
        await connection.execute(
            text(
                "CREATE TABLE categories ("
                "id INTEGER PRIMARY KEY, "
                "parent_id INTEGER REFERENCES categories(id)"
                ")"
            )
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            dependencies = await discover_table_dependencies(
                session,
                tables=["categories"],
            )
    finally:
        await engine.dispose()

    assert len(dependencies) == 1
    assert dependencies[0].dependent == "categories"
    assert dependencies[0].dependency == "categories"


@pytest.mark.asyncio
async def test_reference_outside_inventory_is_rejected() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.execute(text("PRAGMA foreign_keys = ON"))
        await connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        await connection.execute(
            text(
                "CREATE TABLE portfolios ("
                "id INTEGER PRIMARY KEY, "
                "user_id INTEGER REFERENCES users(id)"
                ")"
            )
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            with pytest.raises(ValueError, match="outside inventory: users"):
                await discover_table_dependencies(
                    session,
                    tables=["portfolios"],
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_table_names_do_not_duplicate_introspection() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE assets (id INTEGER PRIMARY KEY)"))

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
            dependencies = await discover_table_dependencies(
                session,
                tables=["assets", "assets"],
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture_statement)
        await engine.dispose()

    assert dependencies == []
    assert sum(statement.upper().startswith("PRAGMA FOREIGN_KEY_LIST") for statement in statements) == 1


def test_empty_table_name_is_rejected() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def run() -> None:
        async with session_factory() as session:
            await discover_table_dependencies(session, tables=[""])

    with pytest.raises(ValueError, match="cannot be empty"):
        import asyncio

        asyncio.run(run())
