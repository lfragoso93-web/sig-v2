"""SuperAdmin surface for the single SGI system bootstrap."""
from __future__ import annotations

import logging
import os
import inspect
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.distributed_job_lock import (
    read_scheduler_job_history,
    read_scheduler_job_statuses,
    scheduler_execution_source,
)
from app.models.user import User
from app.routers.admin import require_superadmin
from app.services.system_bootstrap_execution_context import (
    BOOTSTRAP_COMMIT_SHA_ENV,
    DEFAULT_BOOTSTRAP_COMMIT_SHA,
)
from app.services.system_bootstrap_service import (
    BOOTSTRAP_SCHEMA_VERSION,
    CANONICAL_BOOTSTRAP_STAGES,
)
from app.services.system_bootstrap_trigger_service import (
    bootstrap_launch_reserved,
    reserve_system_bootstrap_launch,
    run_reserved_system_bootstrap,
)
from app.services.system_readiness_service import get_bootstrap_readiness
from app.services.user_test_readiness_service import (
    build_user_test_readiness,
)
from app.core.scheduler import scheduler

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-bootstrap"])

_SCHEDULED_JOB_STATUS_BINDINGS = (
    ("update_quotes_intraday_full_hour", "update_quotes_intraday", "Cotações de mercado", True),
    ("update_crypto_quotes_offhours_weekdays", "update_crypto_quotes", "Cotações de cripto fora do pregão", True),
    ("update_crypto_quotes_weekends", "update_crypto_quotes", "Cotações de cripto no fim de semana", True),
    ("persist_daily_close_prices", "persist_daily_close_prices", "Fechamento de preços", True),
    ("sync_benchmark_rates_daily", "sync_benchmark_rates_daily", "Benchmarks macroeconômicos", True),
    ("sync_ibov_benchmark_daily", "sync_ibov_benchmark_daily", "Fechamento do Ibovespa", True),
    ("persist_treasury_daily_close", "persist_treasury_daily_close", "Fechamento do Tesouro Direto", True),
    ("notify_daily_dividend_payments", "notify_daily_dividend_payments", "Resumo diário de proventos por e-mail", True),
    ("sync_asset_dividends_morning", "sync_asset_dividends", "Coleta global de proventos", True),
    ("sync_corporate_events_daily", "sync_corporate_events", "Coleta global de eventos corporativos", True),
    ("portfolio_snapshot_auto_maintenance", "portfolio_snapshot_auto_maintenance", "Manutenção de snapshots e TWR", True),
    ("refresh_asset_fundamentals_daily", "refresh_asset_fundamentals_daily", "Indicadores fundamentalistas", True),
    ("audit_b3_market_calendar_monthly", "audit_b3_market_calendar", "Auditoria mensal do calendário B3", settings.ENABLE_B3_MARKET_CALENDAR_MONTHLY_AUDIT),
)

_MANUAL_JOB_BINDINGS = frozenset(job_id for job_id, _, _, enabled in _SCHEDULED_JOB_STATUS_BINDINGS if enabled)


async def _run_manual_scheduler_job(job_id: str, actor_user_id: int) -> None:
    job = scheduler.get_job(job_id)
    if job is None:
        raise RuntimeError("scheduled_job_not_active")
    with scheduler_execution_source("manual", actor_user_id):
        result = job.func(*job.args, **job.kwargs)
        if inspect.isawaitable(result):
            await result


class BootstrapTriggerRequest(BaseModel):
    """Payload para acionamento do bootstrap pelo SuperAdmin."""

    commit_sha: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{40}$",
        description="SHA opcional de 40 dígitos hexadecimais",
    )
    stages: list[str] | None = Field(
        default=None,
        description="Lista opcional de IDs de etapas para execução seletiva",
    )


@router.get("/bootstrap/status")
async def admin_system_bootstrap_status(
    _: User = Depends(require_superadmin),
):
    readiness = get_bootstrap_readiness()
    return {
        **readiness.to_dict(),
        "launch_reserved": bootstrap_launch_reserved(),
    }


@router.get("/scheduler/status")
async def admin_scheduler_status(
    _: User = Depends(require_superadmin),
):
    """Expose configured schedules and their latest Redis-backed run status."""
    configured_jobs = {job.id: job for job in scheduler.get_jobs()}
    lock_names = tuple(
        sorted({lock_name for _, lock_name, _, _ in _SCHEDULED_JOB_STATUS_BINDINGS})
    )
    statuses = await read_scheduler_job_statuses(lock_names)
    jobs = []
    for job_id, lock_name, name, enabled in _SCHEDULED_JOB_STATUS_BINDINGS:
        configured = configured_jobs.get(job_id)
        run_status = statuses.get(lock_name, {})
        jobs.append(
            {
                "id": job_id,
                "name": name,
                "enabled": bool(enabled and configured),
                "next_run_at": (
                    configured.next_run_time.isoformat()
                    if configured and configured.next_run_time
                    else None
                ),
                "last_status": run_status.get("status", "never_run"),
                "last_started_at": run_status.get("last_started_at") or None,
                "last_finished_at": run_status.get("last_finished_at") or None,
                "duration_ms": run_status.get("duration_ms") or None,
                "last_error_type": run_status.get("last_error_type") or None,
                "lease_ttl_seconds": run_status.get("lease_ttl_seconds") or None,
                "trigger_source": run_status.get("trigger_source") or None,
                "triggered_by_user_id": run_status.get("triggered_by_user_id") or None,
            }
        )
    return {
        "timezone": "America/Sao_Paulo",
        "status_retention_days": 90,
        "status_store_available": len(statuses) == len(lock_names),
        "jobs": jobs,
    }


@router.get("/scheduler/{job_id}/history")
async def admin_scheduler_history(
    job_id: str,
    limit: int = Query(30, ge=1, le=100),
    _: User = Depends(require_superadmin),
):
    binding = next(
        (item for item in _SCHEDULED_JOB_STATUS_BINDINGS if item[0] == job_id),
        None,
    )
    if binding is None:
        raise HTTPException(status_code=404, detail="Agendamento desconhecido")
    job = await read_scheduler_job_history(binding[1], limit=limit)
    return {"job_id": job_id, "runs": job}


@router.post("/scheduler/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def admin_run_scheduler_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    actor: User = Depends(require_superadmin),
):
    binding = next(
        (item for item in _SCHEDULED_JOB_STATUS_BINDINGS if item[0] == job_id),
        None,
    )
    if binding is None or job_id not in _MANUAL_JOB_BINDINGS:
        raise HTTPException(status_code=404, detail="Agendamento desconhecido")
    if not binding[3]:
        raise HTTPException(status_code=409, detail="Agendamento desativado")
    configured = next((job for job in scheduler.get_jobs() if job.id == job_id), None)
    if configured is None:
        raise HTTPException(status_code=409, detail="Agendamento não está ativo")
    background_tasks.add_task(_run_manual_scheduler_job, job_id, actor.id)
    return {"status": "accepted", "job_id": job_id}


@router.get("/bootstrap/user-test-readiness")
async def admin_user_test_readiness(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    report = await build_user_test_readiness(db)
    return report.to_dict()


@router.post("/bootstrap", status_code=status.HTTP_202_ACCEPTED)
async def admin_trigger_system_bootstrap(
    background_tasks: BackgroundTasks,
    payload: BootstrapTriggerRequest | None = None,
    commit_sha: str | None = Query(
        None,
        pattern=r"^[0-9a-f]{40}$",
        description="SHA opcional que identifica esta execução",
    ),
    stages: list[str] | None = Query(
        None,
        description="Lista opcional de IDs de etapas para execução seletiva",
    ),
    _: User = Depends(require_superadmin),
):
    actual_sha = (
        (payload.commit_sha if payload and payload.commit_sha else None)
        or commit_sha
        or os.getenv(BOOTSTRAP_COMMIT_SHA_ENV, "").strip().lower()
        or getattr(settings, "APP_COMMIT_SHA", "").strip().lower()
        or DEFAULT_BOOTSTRAP_COMMIT_SHA
    )
    if len(actual_sha) != 40:
        actual_sha = DEFAULT_BOOTSTRAP_COMMIT_SHA

    actual_stages = (
        payload.stages if payload and payload.stages else None
    ) or stages

    if actual_stages:
        valid_ids = {s.id for s in CANONICAL_BOOTSTRAP_STAGES}
        unknown = set(actual_stages) - valid_ids
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Etapas desconhecidas: {sorted(unknown)}. "
                    f"Válidas: {sorted(valid_ids)}"
                ),
            )

    if not reserve_system_bootstrap_launch(actual_sha, actual_stages):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="bootstrap global ja reservado ou em execucao",
        )

    background_tasks.add_task(run_reserved_system_bootstrap)
    return {
        "status": "accepted",
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "commit_sha": actual_sha,
        "stages": actual_stages,
        "detail": (
            f"bootstrap seletivo ({len(actual_stages)} etapas) reservado"
            if actual_stages
            else "bootstrap global reservado para execucao"
        ),
    }
