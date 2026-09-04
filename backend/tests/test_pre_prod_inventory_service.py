from __future__ import annotations

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.services.pre_prod_inventory_service import build_pre_prod_inventory


@pytest.mark.asyncio
async def test_inventory_is_read_only_and_reports_canonical_findings() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as connection:
        await connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        await connection.execute(text("CREATE TABLE assets (id INTEGER PRIMARY KEY)"))
        await connection.execute(
            text(
                "CREATE TABLE asset_aliases ("
                "id INTEGER PRIMARY KEY, asset_id INTEGER, "
                "alias_ticker TEXT, asset_type TEXT)"
            )
        )
        await connection.execute(
            text(
                "CREATE TABLE asset_prices ("
                "id INTEGER PRIMARY KEY, asset_id INTEGER, timestamp TEXT)"
            )
        )
        await connection.execute(
            text(
                "CREATE TABLE portfolio_snapshots ("
                "id INTEGER PRIMARY KEY, portfolio_id INTEGER, snapshot_date TEXT)"
            )
        )
        await connection.execute(text("INSERT INTO assets (id) VALUES (1)"))
        await connection.execute(
            text(
                "INSERT INTO asset_aliases "
                "(id, asset_id, alias_ticker, asset_type) VALUES "
                "(1, 1, 'ABCD3', 'ACAO'), "
                "(2, 1, 'abcd3', 'ACAO'), "
                "(3, 999, 'ORPH3', 'ACAO')"
            )
        )
        await connection.execute(
            text(
                "INSERT INTO asset_prices (id, asset_id, timestamp) VALUES "
                "(1, 1, '2026-07-20T00:00:00'), "
                "(2, 1, '2026-07-20T00:00:00'), "
                "(3, 999, '2026-07-20T00:00:00')"
            )
        )
        await connection.execute(
            text(
                "INSERT INTO portfolio_snapshots "
                "(id, portfolio_id, snapshot_date) VALUES "
                "(1, 1, '2026-07-20'), (2, 1, '2026-07-20')"
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
            report = await build_pre_prod_inventory(session)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture_statement)
        await engine.dispose()

    assert report.schema_version == "pre-prod-inventory.v2"
    assert report.mode == "dry-run"
    assert report.safety == {
        "read_only": True,
        "writes_executed": 0,
        "cleanup_executed": False,
        "rebuild_executed": False,
    }

    findings = {item.code: item.count for item in report.findings}
    assert findings == {
        "duplicate_asset_aliases": 1,
        "orphan_asset_aliases": 1,
        "orphan_asset_prices": 1,
        "duplicate_asset_prices": 1,
        "duplicate_portfolio_snapshots": 1,
    }

    assert all(table.rationale for table in report.tables)

    write_verbs = {"INSERT", "UPDATE", "DELETE", "TRUNCATE", "DROP", "ALTER", "CREATE"}
    executed_verbs = {
        statement.split(maxsplit=1)[0].upper()
        for statement in statements
        if statement
    }
    assert executed_verbs.isdisjoint(write_verbs)


@pytest.mark.asyncio
async def test_inventory_can_preserve_supplied_read_only_transaction() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            await session.begin()
            await build_pre_prod_inventory(
                session,
                rollback_supplied_session=False,
            )

            assert session.in_transaction()
            await session.rollback()
    finally:
        await engine.dispose()


@pytest.mark.parametrize(
    ("table_name", "classification"),
    [
        ("users", "preserved"),
        ("goal_allocations", "preserved"),
        ("irpf_reports", "preserved"),
        ("transactions", "export_before_cleanup"),
        ("corporate_events", "export_before_cleanup"),
        ("fixed_income_investments", "export_before_cleanup"),
        ("asset_prices", "rebuildable"),
        ("asset_universe_memberships", "rebuildable"),
        ("fx_rates", "rebuildable"),
        ("future_table", "unclassified"),
    ],
)
def test_inventory_classification_is_exposed_in_report(
    table_name: str,
    classification: str,
) -> None:
    from app.services.pre_prod_inventory_service import _classify_table

    assert _classify_table(table_name) == classification


def test_unknown_table_has_blocking_review_rationale() -> None:
    from app.services.pre_prod_inventory_service import _table_policy

    classification, rationale = _table_policy("future_table")

    assert classification == "unclassified"
    assert "revisão arquitetural" in rationale
