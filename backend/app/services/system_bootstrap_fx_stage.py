"""Estágio cambial canônico do bootstrap global."""
from __future__ import annotations

from datetime import UTC, date, datetime

from app.core.database import AsyncSessionLocal
from app.services.pre_prod_fx_seed_contract import validate_fx_seed_identity
from app.services.pre_prod_fx_seed_service import run_pre_prod_fx_seed
from app.services.system_bootstrap_execution_context import (
    SystemBootstrapExecutionContext,
)

# O par USD-BRL só é semanticamente válido a partir da entrada do Real.
USD_BRL_HISTORY_START_DATE = date(1994, 7, 1)


async def run_system_bootstrap_fx_stage(
    context: SystemBootstrapExecutionContext,
    *,
    end_date: date | None = None,
) -> str:
    """Reconstrói a maior cobertura válida de USD-BRL via PTAX oficial."""
    validate_fx_seed_identity(
        run_id=context.run_id,
        branch=context.branch,
        commit_sha=context.commit_sha,
    )
    target_end = end_date or datetime.now(UTC).date()

    async with AsyncSessionLocal() as lock_db, AsyncSessionLocal() as work_db:
        result = await run_pre_prod_fx_seed(
            run_id=context.run_id,
            branch=context.branch,
            commit_sha=context.commit_sha,
            start_date=USD_BRL_HISTORY_START_DATE,
            end_date=target_end,
            lock_db=lock_db,
            work_db=work_db,
        )

    if not result.ok:
        raise RuntimeError("estágio cambial concluiu com achados bloqueantes")

    pair = result.after.pairs[0] if result.after.pairs else None
    coverage = (
        f"{pair.first_date}..{pair.last_date} rows={pair.rows}"
        if pair is not None
        else "sem cobertura"
    )
    return (
        f"schema={result.schema_version} source={result.source} "
        f"rate_type={result.rate_type} coverage={coverage}"
    )
