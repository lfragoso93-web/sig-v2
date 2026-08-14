"""Orquestracao manual completa da base canonica de mercado do SGI."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from time import monotonic
from typing import Any, Awaitable, Callable

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


@dataclass
class RebuildStepResult:
    name: str
    ok: bool
    duration_seconds: float
    result: Any = None
    error: str | None = None


@dataclass
class FullMarketRebuildResult:
    started_at: str
    finished_at: str | None = None
    duration_seconds: float = 0.0
    ok: bool = True
    steps: list[RebuildStepResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "ok": self.ok,
            "steps": [
                {
                    "name": step.name,
                    "ok": step.ok,
                    "duration_seconds": step.duration_seconds,
                    "result": _jsonable(step.result),
                    "error": step.error,
                }
                for step in self.steps
            ],
        }


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _result_error(result: Any) -> str | None:
    payload = _jsonable(result)
    if not isinstance(payload, dict):
        return None
    errors = payload.get("errors")
    if isinstance(errors, int) and errors > 0:
        return f"errors={errors}"
    if isinstance(errors, (list, tuple, set)) and errors:
        return f"errors={len(errors)}"
    if isinstance(errors, str) and errors.strip():
        return errors.strip()
    failed = payload.get("assets_failed")
    if isinstance(failed, int) and failed > 0:
        return f"assets_failed={failed}"
    assets = payload.get("assets")
    if isinstance(assets, list):
        asset_errors = sum(
            1 for item in assets
            if isinstance(item, dict) and item.get("error")
        )
        if asset_errors:
            return f"asset_errors={asset_errors}"
    return None


def _compact_result(result: Any) -> Any:
    payload = _jsonable(result)
    if not isinstance(payload, dict):
        return payload
    compact = dict(payload)
    assets = compact.pop("assets", None)
    if isinstance(assets, list):
        compact["assets_count"] = len(assets)
        compact["asset_errors"] = sum(
            1 for item in assets
            if isinstance(item, dict) and item.get("error")
        )
    history = compact.get("history")
    if isinstance(history, dict) and len(history) > 20:
        compact["history_count"] = len(history)
        compact["history_nonzero"] = sum(1 for value in history.values() if value)
        compact.pop("history", None)
    return compact


async def _run_step(
    summary: FullMarketRebuildResult,
    name: str,
    operation: Callable[[], Awaitable[Any]],
) -> None:
    started = monotonic()
    logger.info("[full_market_rebuild] INICIO etapa=%s", name)
    try:
        result = await operation()
        duration = round(monotonic() - started, 3)
        internal_error = _result_error(result)
        step_ok = internal_error is None
        if not step_ok:
            summary.ok = False
        summary.steps.append(
            RebuildStepResult(
                name=name,
                ok=step_ok,
                duration_seconds=duration,
                result=result,
                error=internal_error,
            )
        )
        logger.log(
            logging.INFO if step_ok else logging.ERROR,
            "[full_market_rebuild] %s etapa=%s duracao=%.3fs resultado=%s",
            "OK" if step_ok else "PARCIAL",
            name,
            duration,
            _compact_result(result),
        )
    except Exception as exc:
        duration = round(monotonic() - started, 3)
        summary.ok = False
        summary.steps.append(
            RebuildStepResult(
                name=name,
                ok=False,
                duration_seconds=duration,
                error=str(exc),
            )
        )
        logger.exception(
            "[full_market_rebuild] ERRO etapa=%s duracao=%.3fs",
            name,
            duration,
        )


async def _sync_global_asset_prices() -> dict[str, Any]:
    from app.services.asset_price_global_backfill_service import run_global_asset_price_backfill
    return await run_global_asset_price_backfill()


async def _sync_treasury() -> dict[str, Any]:
    from app.services.treasury_catalog_service import seed_treasury_assets
    from app.services.treasury_official_history_service import rebuild_official_treasury_history
    from app.services.treasury_price_history_service import update_treasury_latest_prices

    async with AsyncSessionLocal() as db:
        catalog = await seed_treasury_assets(db)
    history = await rebuild_official_treasury_history()
    async with AsyncSessionLocal() as db:
        latest = await update_treasury_latest_prices(db)
    return {
        "catalog": _jsonable(catalog),
        "history": history,
        "latest_prices": len(latest),
    }


async def _sync_benchmarks() -> dict[str, int]:
    from app.services.benchmark_rate_service import import_missing_benchmark_history
    async with AsyncSessionLocal() as db:
        return await import_missing_benchmark_history(db)


async def _rebuild_all_twr_snapshots() -> dict[str, int]:
    from app.services.portfolio_snapshot_twr_service import backfill_snapshots_with_returns

    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(Portfolio.id)
            .join(Transaction, Transaction.portfolio_id == Portfolio.id)
            .where(Portfolio.is_active.is_(True))
            .distinct()
            .order_by(Portfolio.id.asc())
        )
        portfolio_ids = [row.id for row in rows.all()]

    processed = 0
    snapshots = 0
    errors = 0
    for portfolio_id in portfolio_ids:
        try:
            async with AsyncSessionLocal() as db:
                snapshots += await backfill_snapshots_with_returns(db, portfolio_id)
            processed += 1
        except Exception:
            errors += 1
            logger.exception(
                "[full_market_rebuild] falha ao reconstruir TWR portfolio=%s",
                portfolio_id,
            )
    return {
        "portfolios": len(portfolio_ids),
        "processed": processed,
        "errors": errors,
        "snapshots": snapshots,
    }


async def _run_maintenance() -> dict[str, int]:
    from app.services.market_data_maintenance_service import run_market_data_maintenance
    async with AsyncSessionLocal() as db:
        return await run_market_data_maintenance(db)


async def _final_coverage_audit() -> dict[str, Any]:
    from app.services.asset_price_coverage_service import summarize_asset_price_coverage
    async with AsyncSessionLocal() as db:
        return await summarize_asset_price_coverage(db, full_history=True)


def _step_payload(summary: FullMarketRebuildResult, name: str) -> dict[str, Any]:
    for step in summary.steps:
        if step.name == name and isinstance(step.result, dict):
            return _jsonable(step.result)
    return {}


def _log_operational_summary(summary: FullMarketRebuildResult) -> None:
    prices = _step_payload(summary, "catalog_and_asset_prices")
    treasury = _step_payload(summary, "treasury")
    snapshots = _step_payload(summary, "twr_snapshots")
    coverage = _step_payload(summary, "final_coverage_audit")
    maintenance = _step_payload(summary, "maintenance")

    status_counts = coverage.get("status_counts") or coverage.get("by_status") or {}
    history = treasury.get("history") or {}
    logger.info("=" * 72)
    logger.info("SGI V2 REBUILD SUMMARY")
    logger.info("assets_audited=%s prices_requested=%s prices_inserted=%s",
                prices.get("audited", 0), prices.get("requested", 0), prices.get("inserted", 0))
    logger.info("treasury_official=%s treasury_history_imported=%s treasury_latest=%s",
                history.get("official_symbols", 0), history.get("imported", 0), treasury.get("latest_prices", 0))
    logger.info("snapshots=%s portfolios=%s coverage_needs_sync=%s",
                snapshots.get("snapshots", 0), snapshots.get("processed", 0), coverage.get("needs_sync", 0))
    logger.info("coverage_status=%s", status_counts)
    logger.info("maintenance=%s", maintenance)
    logger.info("duration_seconds=%.3f ok=%s", summary.duration_seconds, summary.ok)
    logger.info("=" * 72)


async def run_full_market_rebuild() -> FullMarketRebuildResult:
    started_dt = datetime.now(timezone.utc)
    started_clock = monotonic()
    summary = FullMarketRebuildResult(started_at=started_dt.isoformat())

    logger.info("=" * 72)
    logger.info("SGI V2 FULL MARKET REBUILD - INICIO")
    logger.info("=" * 72)

    await _run_step(summary, "catalog_and_asset_prices", _sync_global_asset_prices)
    await _run_step(summary, "treasury", _sync_treasury)
    await _run_step(summary, "benchmarks", _sync_benchmarks)
    await _run_step(summary, "twr_snapshots", _rebuild_all_twr_snapshots)
    await _run_step(summary, "maintenance", _run_maintenance)
    await _run_step(summary, "final_coverage_audit", _final_coverage_audit)

    finished_dt = datetime.now(timezone.utc)
    summary.finished_at = finished_dt.isoformat()
    summary.duration_seconds = round(monotonic() - started_clock, 3)

    logger.info("=" * 72)
    logger.info(
        "SGI V2 FULL MARKET REBUILD - FIM ok=%s duracao=%.3fs",
        summary.ok,
        summary.duration_seconds,
    )
    logger.info("=" * 72)
    _log_operational_summary(summary)
    return summary
