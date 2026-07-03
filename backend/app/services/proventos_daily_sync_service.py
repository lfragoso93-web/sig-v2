"""
proventos_daily_sync_service.py

Sincronização diária de eventos/proventos de renda variável nacional.

Objetivo:
  - coletar eventos globais dos ativos nacionais já cadastrados;
  - atualizar AssetDividend de forma idempotente;
  - materializar automaticamente os eventos para carteiras com posição.

Este serviço é usado pelo scheduler diário e não depende da página de Proventos.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.services.dividend_backfill_service import run_backfill, materialize_asset_dividends

logger = logging.getLogger(__name__)

NATIONAL_EVENT_TYPES = {
    AssetType.ACAO.value,
    AssetType.FII.value,
    AssetType.ETF_NACIONAL.value,
    AssetType.BDR.value,
}

SYNC_CONCURRENCY = 3
SYNC_BATCH_DELAY = 2.0


@dataclass
class ProventosDailySyncResult:
    assets_scanned: int = 0
    assets_synced: int = 0
    assets_failed: int = 0
    materialized: int = 0
    errors: list[str] = field(default_factory=list)


async def _sync_asset_events(db: AsyncSession, ticker: str, asset_type: str) -> bool:
    try:
        await run_backfill(db, ticker, asset_type)
        return True
    except Exception as exc:
        logger.error("[proventos_daily] falha ao sincronizar %s/%s: %s", ticker, asset_type, exc)
        return False


async def run_daily_proventos_sync(
    db: AsyncSession,
    asset_types: set[str] | None = None,
    concurrency: int = SYNC_CONCURRENCY,
) -> ProventosDailySyncResult:
    """
    Sincroniza proventos/eventos globais para ativos nacionais cadastrados.

    Importante: `run_backfill` já cria/atualiza AssetDividend e também materializa
    carteiras que possuam o ticker. No final rodamos uma materialização global
    leve para reconciliar vínculos a partir dos eventos globais já salvos.
    """
    wanted = asset_types or NATIONAL_EVENT_TYPES
    result = ProventosDailySyncResult()

    rows = await db.execute(
        select(Asset.ticker, Asset.asset_type)
        .where(Asset.asset_type.in_(sorted(wanted)))
        .order_by(Asset.asset_type, Asset.ticker)
    )
    pairs = [(str(t).upper(), str(at)) for t, at in rows.all() if t and at]
    pairs = sorted(set(pairs), key=lambda x: (x[1], x[0]))
    result.assets_scanned = len(pairs)

    if not pairs:
        logger.info("[proventos_daily] nenhum ativo nacional elegível encontrado")
        return result

    logger.info("[proventos_daily] iniciando sync de %s ativos", len(pairs))

    # Usa sessões separadas por ativo para que falha/rollback de um ticker não
    # contamine a sessão principal nem interrompa todo o job.
    from app.core.database import AsyncSessionLocal

    for i in range(0, len(pairs), concurrency):
        batch = pairs[i:i + concurrency]

        async def _run_one(ticker: str, asset_type: str) -> tuple[str, bool]:
            async with AsyncSessionLocal() as item_db:
                ok = await _sync_asset_events(item_db, ticker, asset_type)
                return ticker, ok

        batch_results = await asyncio.gather(
            *[_run_one(ticker, asset_type) for ticker, asset_type in batch],
            return_exceptions=True,
        )

        for item in batch_results:
            if isinstance(item, Exception):
                result.assets_failed += 1
                result.errors.append(str(item))
                continue
            ticker, ok = item
            if ok:
                result.assets_synced += 1
            else:
                result.assets_failed += 1
                result.errors.append(ticker)

        if i + concurrency < len(pairs):
            await asyncio.sleep(SYNC_BATCH_DELAY)

    # Reconciliador final: garante que carteiras existentes reflitam os eventos
    # globais coletados, inclusive em cenários onde os eventos já existiam antes.
    try:
        result.materialized = await materialize_asset_dividends(db=db, commit=True)
    except Exception as exc:
        logger.error("[proventos_daily] falha na materialização final: %s", exc)
        result.errors.append(f"materialize: {exc}")

    logger.info(
        "[proventos_daily] concluído: scanned=%s synced=%s failed=%s materialized=%s",
        result.assets_scanned,
        result.assets_synced,
        result.assets_failed,
        result.materialized,
    )
    return result
