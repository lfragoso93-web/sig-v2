"""Bootstrap global do SGI v2.

Este módulo concentra a sequência de bootstrap inicial do ambiente e produz
um relatório estruturado por etapa. A inclusão de novas etapas deve acontecer
somente quando o gate operacional correspondente estiver liberado.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from app.services.system_bootstrap_execution_context import (
    build_system_bootstrap_execution_context,
)

logger = logging.getLogger(__name__)

BOOTSTRAP_SCHEMA_VERSION = "system-bootstrap.v4"


@dataclass(frozen=True)
class BootstrapStageResult:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class SystemBootstrapReport:
    schema_version: str
    started_at: str
    finished_at: str
    ok: bool
    stages: tuple[BootstrapStageResult, ...]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["stages"] = [asdict(stage) for stage in self.stages]
        return payload


async def _run_stage(
    name: str,
    operation: Callable[[], Awaitable[str]],
) -> BootstrapStageResult:
    try:
        detail = await operation()
        logger.info("[Bootstrap] %s concluído: %s", name, detail)
        return BootstrapStageResult(name=name, ok=True, detail=detail)
    except Exception as exc:
        logger.exception("[Bootstrap] %s falhou", name)
        return BootstrapStageResult(name=name, ok=False, detail=str(exc))


async def _bootstrap_asset_catalog() -> str:
    from app.core.database import AsyncSessionLocal
    from app.services.asset_seed_service import run_asset_seed

    async with AsyncSessionLocal() as db:
        seed = await run_asset_seed(db)
    return (
        f"created={seed.created} updated={seed.updated} "
        f"skipped={seed.skipped} errors={seed.errors}"
    )


async def _bootstrap_treasury_catalog() -> str:
    from app.core.database import AsyncSessionLocal
    from app.services.treasury_catalog_service import seed_treasury_assets

    async with AsyncSessionLocal() as db:
        result = await seed_treasury_assets(db)
    return (
        f"created={result.created} updated={result.updated} "
        f"skipped={result.skipped} consolidated={result.consolidated} "
        f"errors={result.errors}"
    )


async def _bootstrap_treasury_reconciliation() -> str:
    from app.core.database import AsyncSessionLocal
    from app.services.treasury_reconciliation_service import (
        reconcile_treasury_transactions,
    )

    async with AsyncSessionLocal() as db:
        result = await reconcile_treasury_transactions(db)
    return (
        f"scanned={result.scanned} updated_transactions={result.updated_transactions} "
        f"created_assets={result.created_assets} unresolved={result.unresolved} "
        f"errors={result.errors}"
    )


async def _bootstrap_treasury_history() -> str:
    from app.core.database import AsyncSessionLocal
    from app.services.treasury_official_history_service import (
        rebuild_official_treasury_history,
    )

    async with AsyncSessionLocal() as db:
        history = await rebuild_official_treasury_history(db, commit=True)
    return (
        f"primary_source={history.get('primary_source')} "
        f"fallback_source={history.get('fallback_source')} "
        f"imported={history.get('imported', 0)} "
        f"official_imported={history.get('official_imported', 0)} "
        f"fallback_imported={history.get('fallback_imported', 0)} "
        f"required_empty_payloads={history.get('required_empty_payloads', 0)} "
        f"unresolved_assets={len(history.get('unresolved_assets') or [])}"
    )


async def _bootstrap_asset_price_history() -> str:
    from app.models.asset import AssetType
    from app.services.asset_price_global_backfill_service import (
        run_global_asset_price_backfill,
    )
    from app.services.crypto_supported_universe_service import (
        fetch_supported_crypto_tickers,
    )

    supported_crypto = await fetch_supported_crypto_tickers()
    result = await run_global_asset_price_backfill(
        asset_types={AssetType.CRIPTO.value},
        tickers=supported_crypto,
    )
    return str(result)


async def _bootstrap_benchmarks() -> str:
    from app.core.database import AsyncSessionLocal
    from app.services.benchmark_rate_service import import_missing_benchmark_history

    async with AsyncSessionLocal() as db:
        result = await import_missing_benchmark_history(db)
    return str(result)


async def run_system_bootstrap(
    *,
    commit_sha: str | None = None,
    startup_delay_seconds: float = 0.0,
) -> SystemBootstrapReport:
    """Executa as etapas de bootstrap atualmente integradas.

    O v4 acrescenta eventos corporativos globais ao fluxo certificado,
    reutilizando o wrapper dedicado e gated da #254. Proventos e eventos
    corporativos continuam com autorização operacional explícita e falham
    fechados antes de providers quando bloqueados. Um relatório verde ainda
    não autoriza dados reais por si só.
    """
    from app.services.system_bootstrap_corporate_events_stage import (
        run_system_bootstrap_corporate_events_stage,
    )
    from app.services.system_bootstrap_dividends_stage import (
        run_system_bootstrap_dividends_stage,
    )
    from app.services.system_bootstrap_fx_stage import run_system_bootstrap_fx_stage
    from app.services.system_readiness_service import (
        mark_bootstrap_finished,
        mark_bootstrap_running,
    )

    context = build_system_bootstrap_execution_context(commit_sha=commit_sha)

    if startup_delay_seconds > 0:
        await asyncio.sleep(startup_delay_seconds)

    started = datetime.now(timezone.utc)
    mark_bootstrap_running(
        schema_version=BOOTSTRAP_SCHEMA_VERSION,
        started_at=started.isoformat(),
    )

    operations: tuple[tuple[str, Callable[[], Awaitable[str]]], ...] = (
        ("asset_catalog", _bootstrap_asset_catalog),
        ("treasury_catalog", _bootstrap_treasury_catalog),
        ("treasury_reconciliation", _bootstrap_treasury_reconciliation),
        ("treasury_history", _bootstrap_treasury_history),
        ("asset_price_history", _bootstrap_asset_price_history),
        ("benchmarks", _bootstrap_benchmarks),
        ("fx_rates", lambda: run_system_bootstrap_fx_stage(context)),
        (
            "asset_dividends",
            lambda: run_system_bootstrap_dividends_stage(context),
        ),
        (
            "corporate_events",
            lambda: run_system_bootstrap_corporate_events_stage(context),
        ),
    )

    stages: list[BootstrapStageResult] = []
    for name, operation in operations:
        result = await _run_stage(name, operation)
        stages.append(result)
        if not result.ok:
            break

    finished = datetime.now(timezone.utc)
    report = SystemBootstrapReport(
        schema_version=BOOTSTRAP_SCHEMA_VERSION,
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        ok=len(stages) == len(operations) and all(stage.ok for stage in stages),
        stages=tuple(stages),
    )
    mark_bootstrap_finished(report, certified_for_real_data=False)
    return report
