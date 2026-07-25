"""Orquestração transacional do estágio isolado do Tesouro Direto.

Catálogo, histórico e inspeções compartilham uma única sessão de trabalho. Os
serviços reais são executados com ``commit=False``; somente este orquestrador pode
confirmar ou reverter o estágio completo. O advisory lock usa sessão separada para
permanecer ativo durante toda a transação.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pre_prod_treasury_seed_contract import PreProdTreasurySeedResult
from app.services.pre_prod_treasury_seed_inspection import inspect_treasury_seed_state
from app.services.treasury_catalog_v2_service import sync_treasury_catalog_v2
from app.services.treasury_official_history_service import rebuild_official_treasury_history

_TREASURY_SEED_LOCK_KEY = 7_317_202_607_25

CatalogRunner = Callable[[AsyncSession], Awaitable[dict[str, Any]]]
HistoryRunner = Callable[[AsyncSession], Awaitable[dict[str, Any]]]
InspectionRunner = Callable[
    [AsyncSession],
    Awaitable[tuple[Any, Any]],
]


class TreasurySeedAlreadyRunningError(RuntimeError):
    """Indica que outra execução mantém o advisory lock do estágio Tesouro."""


async def _run_real_catalog(db: AsyncSession) -> dict[str, Any]:
    result = await sync_treasury_catalog_v2(db, commit=False)
    return result.to_dict()


async def _run_real_history(db: AsyncSession) -> dict[str, Any]:
    return await rebuild_official_treasury_history(db, commit=False)


def _collect_errors(
    *,
    catalog: dict[str, Any],
    history: dict[str, Any],
    after: Any,
) -> list[str]:
    errors: list[str] = []
    if int(catalog.get("errors", 0) or 0) != 0:
        errors.append("catálogo oficial retornou erros")
    unresolved = history.get("unresolved_assets") or []
    if unresolved:
        errors.append(f"histórico deixou {len(unresolved)} ativos não resolvidos")
    if int(history.get("empty_payloads", 0) or 0) != 0:
        errors.append("histórico retornou payloads vazios")
    integrity_values = (
        after.orphan_prices,
        after.duplicate_prices,
        after.legacy_assets,
        after.legacy_prices,
    )
    if any(integrity_values):
        errors.append("integridade final do Tesouro não foi reconciliada")
    return errors


async def run_pre_prod_treasury_seed(
    *,
    lock_db: AsyncSession,
    work_db: AsyncSession,
    catalog_runner: CatalogRunner = _run_real_catalog,
    history_runner: HistoryRunner = _run_real_history,
    inspection_runner: InspectionRunner = inspect_treasury_seed_state,
) -> PreProdTreasurySeedResult:
    """Executa catálogo -> histórico em uma única transação controlada.

    O commit ocorre somente após a inspeção final confirmar ausência de erros e
    divergências de integridade. Qualquer exceção ou resultado inválido executa
    rollback antes da liberação do advisory lock.
    """

    started = datetime.now(timezone.utc)
    started_clock = monotonic()
    acquired = await lock_db.scalar(
        text("SELECT pg_try_advisory_lock(:lock_key)"),
        {"lock_key": _TREASURY_SEED_LOCK_KEY},
    )
    if not acquired:
        raise TreasurySeedAlreadyRunningError("estágio Tesouro já está em execução")

    try:
        before, _before_coverage = await inspection_runner(work_db)
        catalog = await catalog_runner(work_db)
        history = await history_runner(work_db)
        await work_db.flush()
        after, coverage = await inspection_runner(work_db)
        errors = _collect_errors(catalog=catalog, history=history, after=after)

        if errors:
            await work_db.rollback()
        else:
            await work_db.commit()

        finished = datetime.now(timezone.utc)
        return PreProdTreasurySeedResult(
            started_at=started.isoformat(),
            finished_at=finished.isoformat(),
            duration_seconds=round(monotonic() - started_clock, 3),
            ok=not errors,
            before=before,
            after=after,
            coverage=coverage,
            catalog=catalog,
            history=history,
            errors=tuple(errors),
        )
    except BaseException:
        await work_db.rollback()
        raise
    finally:
        await lock_db.execute(
            text("SELECT pg_advisory_unlock(:lock_key)"),
            {"lock_key": _TREASURY_SEED_LOCK_KEY},
        )
