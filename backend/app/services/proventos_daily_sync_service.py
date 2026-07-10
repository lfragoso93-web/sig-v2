"""
proventos_daily_sync_service.py

Sincronização diária de eventos/proventos de renda variável nacional.

Objetivo:
  - coletar eventos globais dos ativos nacionais já cadastrados;
  - atualizar AssetDividend de forma idempotente;
  - complementar o histórico anterior à cobertura da BRAPI;
  - materializar automaticamente os eventos para carteiras com posição.

Este serviço é usado pelo scheduler diário e não depende da página de Proventos.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.services.dividend_backfill_service import run_backfill, materialize_asset_dividends
from app.services.dividend_history_seed_service import seed_full_dividend_history

logger = logging.getLogger(__name__)

NATIONAL_EVENT_TYPES = {
    AssetType.ACAO.value,
    AssetType.FII.value,
    AssetType.ETF_NACIONAL.value,
    AssetType.BDR.value,
}

# Tickers fracionários/direitos/recibos não têm agenda própria de eventos.
# O provento pertence ao ticker principal, por exemplo B3SA3 e não B3SA3F.
_MAIN_EQUITY_RE = re.compile(r"^[A-Z0-9]{4,6}(3|4|5|6|11|31|32|33|34|35)$")

SYNC_CONCURRENCY = 3
SYNC_BATCH_DELAY = 2.0


@dataclass
class ProventosDailySyncResult:
    assets_scanned: int = 0
    assets_synced: int = 0
    assets_failed: int = 0
    assets_skipped: int = 0
    materialized: int = 0
    historical_events: int = 0
    errors: list[str] = field(default_factory=list)


def _is_event_ticker(ticker: str) -> bool:
    t = ticker.upper()
    if t.endswith("F"):
        return False
    if t[-1:] in {"B", "D", "R"}:
        return False
    if t[-2:] in {"97", "98", "99"}:
        return False
    return bool(_MAIN_EQUITY_RE.match(t))


async def _sync_asset_events(db: AsyncSession, ticker: str, asset_type: str) -> tuple[bool, int]:
    try:
        await run_backfill(db, ticker, asset_type)
        historical = await seed_full_dividend_history(db, ticker, asset_type)
        return True, historical
    except Exception as exc:
        logger.error("[proventos_daily] falha ao sincronizar %s/%s: %s", ticker, asset_type, exc)
        return False, 0


async def run_daily_proventos_sync(
    db: AsyncSession,
    asset_types: set[str] | None = None,
    concurrency: int = SYNC_CONCURRENCY,
) -> ProventosDailySyncResult:
    """
    Sincroniza proventos/eventos globais para ativos nacionais cadastrados.

    `run_backfill` opera em modo global quando chamado por este serviço: ele cria
    ou atualiza eventos em AssetDividend. Em seguida, o seed histórico preenche
    datas anteriores à cobertura da BRAPI e materializa os vínculos de Dividend
    das carteiras com posição na data do evento.
    """
    wanted = asset_types or NATIONAL_EVENT_TYPES
    result = ProventosDailySyncResult()

    rows = await db.execute(
        select(Asset.ticker, Asset.asset_type)
        .where(Asset.asset_type.in_(sorted(wanted)))
        .order_by(Asset.asset_type, Asset.ticker)
    )
    raw_pairs = [(str(t).upper(), str(at)) for t, at in rows.all() if t and at]
    unique_pairs = sorted(set(raw_pairs), key=lambda x: (x[1], x[0]))
    pairs = [(ticker, at) for ticker, at in unique_pairs if _is_event_ticker(ticker)]
    result.assets_scanned = len(pairs)
    result.assets_skipped = len(unique_pairs) - len(pairs)

    if result.assets_skipped:
        logger.info(
            "[proventos_daily] %s tickers fracionários/direitos/recibos ignorados no sync de eventos",
            result.assets_skipped,
        )

    if not pairs:
        logger.info("[proventos_daily] nenhum ativo nacional elegível encontrado")
        return result

    logger.info("[proventos_daily] iniciando sync global de eventos para %s ativos", len(pairs))

    from app.core.database import AsyncSessionLocal

    for i in range(0, len(pairs), concurrency):
        batch = pairs[i:i + concurrency]

        async def _run_one(ticker: str, asset_type: str) -> tuple[str, bool, int]:
            async with AsyncSessionLocal() as item_db:
                ok, historical = await _sync_asset_events(item_db, ticker, asset_type)
                return ticker, ok, historical

        batch_results = await asyncio.gather(
            *[_run_one(ticker, asset_type) for ticker, asset_type in batch],
            return_exceptions=True,
        )

        for item in batch_results:
            if isinstance(item, Exception):
                result.assets_failed += 1
                result.errors.append(str(item))
                continue
            ticker, ok, historical = item
            result.historical_events += historical
            if ok:
                result.assets_synced += 1
            else:
                result.assets_failed += 1
                result.errors.append(ticker)

        if i + concurrency < len(pairs):
            await asyncio.sleep(SYNC_BATCH_DELAY)

    try:
        result.materialized = await materialize_asset_dividends(db=db, commit=True)
    except Exception as exc:
        logger.error("[proventos_daily] falha na materialização final: %s", exc)
        result.errors.append(f"materialize: {exc}")

    logger.info(
        "[proventos_daily] concluído: scanned=%s synced=%s failed=%s skipped=%s historical=%s materialized=%s",
        result.assets_scanned,
        result.assets_synced,
        result.assets_failed,
        result.assets_skipped,
        result.historical_events,
        result.materialized,
    )
    return result
