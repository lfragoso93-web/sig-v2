"""Orquestração transacional do estágio isolado de séries macroeconômicas."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.benchmark_rate_service import import_missing_benchmark_history
from app.services.pre_prod_macro_seed_contract import PreProdMacroSeedResult
from app.services.pre_prod_macro_seed_inspection import inspect_macro_seed_state

_MACRO_SEED_LOCK_KEY = 7_317_202_607_26

ImportRunner = Callable[[AsyncSession], Awaitable[dict[str, int]]]
InspectionRunner = Callable[[AsyncSession], Awaitable[Any]]


class MacroSeedAlreadyRunningError(RuntimeError):
    """Indica que outra execução mantém o advisory lock do estágio macro."""


async def _run_real_import(db: AsyncSession) -> dict[str, int]:
    return await import_missing_benchmark_history(db, commit=False)


def _collect_errors(after: Any) -> list[str]:
    errors: list[str] = []
    if after.duplicate_rows:
        errors.append(
            f"rate_history contém {after.duplicate_rows} linha(s) duplicada(s)"
        )
    if after.unsupported_indicators:
        errors.append(
            "rate_history contém indicadores não suportados: "
            + ", ".join(after.unsupported_indicators)
        )
    return errors


async def run_pre_prod_macro_seed(
    *,
    run_id: str,
    branch: str,
    commit_sha: str,
    lock_db: AsyncSession,
    work_db: AsyncSession,
    import_runner: ImportRunner = _run_real_import,
    inspection_runner: InspectionRunner = inspect_macro_seed_state,
) -> PreProdMacroSeedResult:
    """Executa inspeção -> importação -> inspeção em uma transação controlada."""

    started = datetime.now(timezone.utc)
    started_clock = monotonic()
    acquired = await lock_db.scalar(
        text("SELECT pg_try_advisory_lock(:lock_key)"),
        {"lock_key": _MACRO_SEED_LOCK_KEY},
    )
    if not acquired:
        raise MacroSeedAlreadyRunningError(
            "estágio macroeconômico já está em execução"
        )

    try:
        before = await inspection_runner(work_db)
        imported = await import_runner(work_db)
        await work_db.flush()
        after = await inspection_runner(work_db)
        errors = _collect_errors(after)

        if errors:
            await work_db.rollback()
        else:
            await work_db.commit()

        finished = datetime.now(timezone.utc)
        return PreProdMacroSeedResult(
            run_id=run_id,
            branch=branch,
            commit_sha=commit_sha,
            started_at=started.isoformat(),
            finished_at=finished.isoformat(),
            duration_seconds=round(monotonic() - started_clock, 3),
            ok=not errors,
            before=before,
            after=after,
            imported=imported,
            errors=tuple(errors),
        )
    except BaseException:
        await work_db.rollback()
        raise
    finally:
        await lock_db.execute(
            text("SELECT pg_advisory_unlock(:lock_key)"),
            {"lock_key": _MACRO_SEED_LOCK_KEY},
        )
