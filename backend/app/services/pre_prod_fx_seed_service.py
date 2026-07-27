"""Orquestração transacional do estágio isolado de câmbio."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date as DateType, datetime, timezone
from time import monotonic
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pre_prod_fx_seed_contract import PreProdFxSeedResult
from app.services.pre_prod_fx_seed_inspection import inspect_fx_seed_state
from app.services.pre_prod_fx_seed_preparation import (
    FxSeedPreparationResult,
    prepare_pre_prod_fx_seed,
)

_FX_SEED_LOCK_KEY = 7_317_202_607_27

PreparationRunner = Callable[..., Awaitable[FxSeedPreparationResult]]
InspectionRunner = Callable[[AsyncSession], Awaitable[Any]]


class FxSeedAlreadyRunningError(RuntimeError):
    """Indica que outra execução mantém o advisory lock do estágio cambial."""


def _collect_errors(after: Any) -> list[str]:
    errors: list[str] = []
    if after.duplicate_rows:
        errors.append(
            f"fx_rates contém {after.duplicate_rows} linha(s) duplicada(s)"
        )
    if after.unsupported_pairs:
        errors.append(
            "fx_rates contém pares não suportados: "
            + ", ".join(after.unsupported_pairs)
        )
    return errors


async def run_pre_prod_fx_seed(
    *,
    run_id: str,
    branch: str,
    commit_sha: str,
    start_date: str | DateType,
    end_date: str | DateType,
    lock_db: AsyncSession,
    work_db: AsyncSession,
    preparation_runner: PreparationRunner = prepare_pre_prod_fx_seed,
    inspection_runner: InspectionRunner = inspect_fx_seed_state,
) -> PreProdFxSeedResult:
    """Executa inspeção -> preparação -> inspeção em transação controlada."""

    started = datetime.now(timezone.utc)
    started_clock = monotonic()
    acquired = await lock_db.scalar(
        text("SELECT pg_try_advisory_lock(:lock_key)"),
        {"lock_key": _FX_SEED_LOCK_KEY},
    )
    if not acquired:
        raise FxSeedAlreadyRunningError("estágio cambial já está em execução")

    try:
        before = await inspection_runner(work_db)
        prepared = await preparation_runner(
            work_db,
            start_date=start_date,
            end_date=end_date,
        )
        await work_db.flush()
        after = await inspection_runner(work_db)
        errors = _collect_errors(after)

        if errors:
            await work_db.rollback()
        else:
            await work_db.commit()

        finished = datetime.now(timezone.utc)
        return PreProdFxSeedResult(
            run_id=run_id,
            branch=branch,
            commit_sha=commit_sha,
            started_at=started.isoformat(),
            finished_at=finished.isoformat(),
            duration_seconds=round(monotonic() - started_clock, 3),
            ok=not errors,
            before=before,
            after=after,
            imported=prepared.imported_counts(),
            errors=tuple(errors),
        )
    except BaseException:
        await work_db.rollback()
        raise
    finally:
        await lock_db.execute(
            text("SELECT pg_advisory_unlock(:lock_key)"),
            {"lock_key": _FX_SEED_LOCK_KEY},
        )
