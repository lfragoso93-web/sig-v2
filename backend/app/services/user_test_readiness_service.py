"""Readiness read-only para rodadas assistidas com usuarios.

Este servico consolida sinais operacionais sem promover o ambiente para dados
reais. O resultado indica se uma rodada acompanhada pode acontecer e explicita
por que `ready_for_real_data` deve continuar separado.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.pre_prod_inventory_service import build_pre_prod_inventory
from app.services.system_readiness_service import get_bootstrap_readiness

REPORT_SCHEMA_VERSION = "user-test-readiness.v1"
GOALS_RUNTIME_REVISION = "20260910_goals_runtime"

CRITICAL_TABLES = (
    "users",
    "portfolios",
    "transactions",
    "assets",
    "asset_prices",
    "portfolio_snapshots",
    "asset_dividends",
    "corporate_events",
    "goals",
)


@dataclass(frozen=True)
class UserTestReadinessCheck:
    code: str
    status: str
    detail: str
    severity: str = "info"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UserTestReadinessReport:
    schema_version: str
    generated_at: str
    environment: str
    go_for_assisted_user_tests: bool
    ready_for_real_data: bool
    status: str
    checks: list[UserTestReadinessCheck]
    counts: dict[str, int]
    blockers: list[str]
    warnings: list[str]
    safety: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["checks"] = [check.to_dict() for check in self.checks]
        return payload


async def _table_names(session: AsyncSession) -> set[str]:
    dialect = session.get_bind().dialect.name
    if dialect == "sqlite":
        result = await session.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        )
    else:
        result = await session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        )
    return {str(row[0]) for row in result}


async def _count_table(session: AsyncSession, table_name: str) -> int:
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"unsafe table name: {table_name!r}")
    result = await session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
    return int(result.scalar_one())


async def _alembic_revisions(session: AsyncSession, tables: set[str]) -> set[str]:
    if "alembic_version" not in tables:
        return set()
    result = await session.execute(text("SELECT version_num FROM alembic_version"))
    return {str(row[0]) for row in result}


def _append_check(
    checks: list[UserTestReadinessCheck],
    *,
    code: str,
    ok: bool,
    detail: str,
    severity: str = "error",
) -> None:
    checks.append(
        UserTestReadinessCheck(
            code=code,
            status="pass" if ok else "fail",
            detail=detail,
            severity="info" if ok else severity,
        )
    )


async def build_user_test_readiness(
    session: AsyncSession,
) -> UserTestReadinessReport:
    """Monta um relatorio read-only de liberacao para teste assistido."""

    checks: list[UserTestReadinessCheck] = []
    counts: dict[str, int] = {}

    inventory = await build_pre_prod_inventory(
        session,
        rollback_supplied_session=False,
    )
    tables = await _table_names(session)
    revisions = await _alembic_revisions(session, tables)

    for table in CRITICAL_TABLES:
        counts[table] = await _count_table(session, table) if table in tables else 0

    readiness = get_bootstrap_readiness()

    _append_check(
        checks,
        code="database_inventory",
        ok=inventory.totals["blocking_findings"] == 0
        and inventory.totals["unclassified_tables"] == 0,
        detail=(
            f"blocking_findings={inventory.totals['blocking_findings']} "
            f"unclassified_tables={inventory.totals['unclassified_tables']}"
        ),
    )
    _append_check(
        checks,
        code="goals_runtime_schema",
        ok=GOALS_RUNTIME_REVISION in revisions,
        detail=f"required_revision={GOALS_RUNTIME_REVISION} applied={sorted(revisions)}",
    )
    _append_check(
        checks,
        code="assisted_test_data_present",
        ok=counts["users"] > 0
        and counts["portfolios"] > 0
        and counts["transactions"] > 0,
        detail=(
            f"users={counts['users']} portfolios={counts['portfolios']} "
            f"transactions={counts['transactions']}"
        ),
    )
    _append_check(
        checks,
        code="market_history_present",
        ok=counts["assets"] > 0 and counts["asset_prices"] > 0,
        detail=f"assets={counts['assets']} asset_prices={counts['asset_prices']}",
    )
    _append_check(
        checks,
        code="snapshot_history_present",
        ok=counts["portfolio_snapshots"] > 0,
        detail=f"portfolio_snapshots={counts['portfolio_snapshots']}",
        severity="warning",
    )
    _append_check(
        checks,
        code="dividends_seed_present",
        ok=counts["asset_dividends"] > 0,
        detail=f"asset_dividends={counts['asset_dividends']}",
        severity="warning",
    )
    _append_check(
        checks,
        code="corporate_events_seed_present",
        ok=counts["corporate_events"] > 0,
        detail=f"corporate_events={counts['corporate_events']}",
        severity="warning",
    )
    _append_check(
        checks,
        code="real_data_gate_closed",
        ok=not readiness.ready_for_real_data,
        detail=(
            f"state={readiness.state.value} "
            f"ready_for_real_data={readiness.ready_for_real_data}"
        ),
    )
    _append_check(
        checks,
        code="automatic_bootstrap_policy",
        ok=not settings.ENABLE_BOOT_MARKET_SYNC,
        detail=f"ENABLE_BOOT_MARKET_SYNC={settings.ENABLE_BOOT_MARKET_SYNC}",
        severity="warning",
    )

    blockers = [
        check.code
        for check in checks
        if check.status == "fail" and check.severity == "error"
    ]
    warnings = [
        check.code
        for check in checks
        if check.status == "fail" and check.severity == "warning"
    ]
    go_for_assisted = not blockers

    return UserTestReadinessReport(
        schema_version=REPORT_SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        environment=settings.ENVIRONMENT,
        go_for_assisted_user_tests=go_for_assisted,
        ready_for_real_data=readiness.ready_for_real_data,
        status="GO_ASSISTED" if go_for_assisted else "NO_GO",
        checks=checks,
        counts=counts,
        blockers=blockers,
        warnings=warnings,
        safety={
            "read_only": True,
            "writes_executed": 0,
            "promotes_ready_for_real_data": False,
            "allows_real_user_data": False,
        },
    )
