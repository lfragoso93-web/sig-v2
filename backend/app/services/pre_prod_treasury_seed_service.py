"""Orquestração isolada do estágio Tesouro, ainda sem ligação aos serviços reais.

A Issue #208 exige exclusão mútua, ordem explícita e evidência antes/depois.
Neste bloco os executores de catálogo e histórico são dependências obrigatórias:
isso impede que a fundação seja confundida com autorização operacional enquanto o
histórico oficial ainda usa sessões próprias e commits parciais.
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

_TREASURY_SEED_LOCK_KEY = 7_317_202_607_25

CatalogRunner = Callable[[AsyncSession], Awaitable[dict[str, Any]]]
HistoryRunner = Callable[[], Awaitable[dict[str, Any]]]
InspectionRunner = Callable[
    [AsyncSession],
    Awaitable[tuple[Any, Any]],
]


class TreasurySeedAlreadyRunningError(RuntimeError):
    """Indica que outra execução mantém o advisory lock do estágio Tesouro."""


async def run_pre_prod_treasury_seed(
    *,
    lock_db: AsyncSession,
    inspection_db: AsyncSession,
    catalog_db: AsyncSession,
    catalog_runner: CatalogRunner,
    history_runner: HistoryRunner,
    inspection_runner: InspectionRunner = inspect_treasury_seed_state,
) -> PreProdTreasurySeedResult:
    """Executa o esqueleto auditável catálogo -> histórico sob lock dedicado.

    Os runners são obrigatórios e não possuem defaults de produção. A ligação com os
    serviços reais só será feita depois que o histórico suportar a estratégia de falha
    segura definida pela Issue #208.
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
        before, _before_coverage = await inspection_runner(inspection_db)
        catalog = await catalog_runner(catalog_db)
        history = await history_runner()
        after, coverage = await inspection_runner(inspection_db)

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
    finally:
        await lock_db.execute(
            text("SELECT pg_advisory_unlock(:lock_key)"),
            {"lock_key": _TREASURY_SEED_LOCK_KEY},
        )
