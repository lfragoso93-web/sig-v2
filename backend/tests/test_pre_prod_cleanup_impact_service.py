from __future__ import annotations

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.pre_prod_cleanup_impact_service import (
    build_pre_prod_cleanup_impact,
)


_WRITE_VERBS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "TRUNCATE",
    "DROP",
    "ALTER",
    "CREATE",
}


@pytest.mark.asyncio
async def test_cleanup_impact_builds_from_inventory_without_writes() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        await connection.execute(
            text("CREATE TABLE transactions (id INTEGER PRIMARY KEY)")
        )
        await connection.execute(
            text("CREATE TABLE asset_prices (id INTEGER PRIMARY KEY)")
        )
        await connection.execute(text("INSERT INTO users (id) VALUES (1)"))
        await connection.execute(
            text("INSERT INTO transactions (id) VALUES (1), (2)")
        )
        await connection.execute(
            text("INSERT INTO asset_prices (id) VALUES (1), (2), (3)")
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
            report = await build_pre_prod_cleanup_impact(
                branch="stable-15jun",
                commit_sha="a" * 40,
                session=session,
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture_statement)
        await engine.dispose()

    assert report.schema_version == "pre-prod-cleanup-impact.v1"
    assert report.inventory_schema_version == "pre-prod-inventory.v2"
    assert report.branch == "stable-15jun"
    assert report.commit_sha == "a" * 40

    actions = {table.name: table.proposed_action for table in report.tables}
    assert actions == {
        "asset_prices": "clean_and_rebuild",
        "transactions": "export_required",
        "users": "preserve",
    }
    assert report.totals.tables == 3
    assert report.totals.rows == 6
    assert report.totals.preserved_tables == 1
    assert report.totals.export_required_tables == 1
    assert report.totals.rebuildable_tables == 1
    assert report.totals.blocked_tables == 0
    assert report.ok is True
    assert report.blockers == []
    assert report.safety.writes_executed == 0

    executed_verbs = {
        statement.split(maxsplit=1)[0].upper()
        for statement in statements
        if statement
    }
    assert executed_verbs.isdisjoint(_WRITE_VERBS)


@pytest.mark.asyncio
async def test_cleanup_impact_rolls_back_supplied_session() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            await session.begin()
            await build_pre_prod_cleanup_impact(
                branch="stable-15jun",
                commit_sha="b" * 40,
                session=session,
            )

            assert not session.in_transaction()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cleanup_impact_blocks_unclassified_table() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.execute(
            text("CREATE TABLE future_table (id INTEGER PRIMARY KEY)")
        )

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            report = await build_pre_prod_cleanup_impact(
                branch="stable-15jun",
                commit_sha="c" * 40,
                session=session,
            )
    finally:
        await engine.dispose()

    assert report.ok is False
    assert report.blockers == ["future_table"]
    assert report.totals.blocked_tables == 1
    assert report.tables[0].proposed_action == "block"
