"""
Sincronizacao diaria de eventos/proventos de renda variavel nacional.

O servico coleta eventos globais, atualiza AssetDividend de forma idempotente,
complementa historico, materializa os eventos nas carteiras elegiveis e invalida
os consumidores financeiros afetados.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction
from app.services.dividend_backfill_service import run_backfill, materialize_asset_dividends

logger = logging.getLogger(__name__)

NATIONAL_EVENT_TYPES = {
    AssetType.ACAO.value,
    AssetType.FII.value,
    AssetType.ETF_NACIONAL.value,
    AssetType.BDR.value,
}

_MAIN_EQUITY_RE = re.compile(r"^[A-Z0-9]{4,6}(3|4|5|6|11|31|32|33|34|35)$")
SYNC_CONCURRENCY = 10
SYNC_BATCH_DELAY = 0.5
MATERIALIZE_TICKER_BATCH_SIZE = 50


@dataclass
class ProventosDailySyncResult:
    assets_scanned: int = 0
    assets_synced: int = 0
    assets_failed: int = 0
    assets_skipped: int = 0
    materialized: int = 0
    historical_events: int = 0
    portfolios_invalidated: int = 0
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


def _chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


async def _sync_asset_events(db: AsyncSession, ticker: str, asset_type: str) -> tuple[bool, int]:
    from app.services.dividend_history_seed_service import seed_full_dividend_history

    try:
        await run_backfill(db, ticker, asset_type)
        historical = await seed_full_dividend_history(db, ticker, asset_type)
        return True, historical
    except Exception as exc:
        logger.error("[proventos_daily] falha ao sincronizar %s/%s: %s", ticker, asset_type, exc)
        return False, 0


async def _invalidate_affected_portfolios(db: AsyncSession, tickers: list[str]) -> int:
    from app.services.portfolio_service import invalidate_portfolio_cache

    if not tickers:
        return 0
    rows = await db.execute(
        select(Transaction.portfolio_id)
        .where(Transaction.ticker.in_(tickers))
        .distinct()
    )
    portfolio_ids = [row.portfolio_id for row in rows.all()]
    for portfolio_id in portfolio_ids:
        await invalidate_portfolio_cache(portfolio_id)
    return len(portfolio_ids)


async def load_proventos_sync_pairs(
    db: AsyncSession,
    *,
    asset_types: set[str] | None = None,
    only_held: bool = True,
) -> tuple[list[tuple[str, str]], int]:
    """Carrega tickers elegíveis sem varrer o catálogo quando há carteira."""
    wanted = asset_types or NATIONAL_EVENT_TYPES
    if only_held:
        stmt = (
            select(Transaction.ticker, Transaction.asset_type)
            .where(Transaction.asset_type.in_(sorted(wanted)))
            .distinct()
            .order_by(Transaction.asset_type, Transaction.ticker)
        )
    else:
        stmt = (
            select(Asset.ticker, Asset.asset_type)
            .where(Asset.asset_type.in_(sorted(wanted)))
            .order_by(Asset.asset_type, Asset.ticker)
        )

    rows = await db.execute(stmt)
    raw_pairs = [
        (str(ticker).upper(), str(asset_type))
        for ticker, asset_type in rows.all()
        if ticker and asset_type
    ]
    unique_pairs = sorted(set(raw_pairs), key=lambda item: (item[1], item[0]))
    eligible_pairs = [
        (ticker, asset_type)
        for ticker, asset_type in unique_pairs
        if _is_event_ticker(ticker)
    ]
    return eligible_pairs, len(unique_pairs) - len(eligible_pairs)


async def run_daily_proventos_sync(
    db: AsyncSession,
    asset_types: set[str] | None = None,
    concurrency: int = SYNC_CONCURRENCY,
    *,
    only_held: bool = True,
) -> ProventosDailySyncResult:
    """Sincroniza eventos e materializa apenas o universo operacional solicitado."""
    result = ProventosDailySyncResult()

    pairs, skipped = await load_proventos_sync_pairs(
        db,
        asset_types=asset_types,
        only_held=only_held,
    )
    result.assets_scanned = len(pairs)
    result.assets_skipped = skipped

    if result.assets_skipped:
        logger.info(
            "[proventos_daily] %s tickers fracionarios/direitos/recibos ignorados no sync de eventos",
            result.assets_skipped,
        )

    if not pairs:
        logger.info("[proventos_daily] nenhum ativo nacional elegivel encontrado")
        return result

    concurrency = max(1, min(int(concurrency or SYNC_CONCURRENCY), 10))
    logger.info(
        "[proventos_daily] iniciando sync global de eventos para %s ativos concurrency=%s",
        len(pairs),
        concurrency,
    )

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

    materialize_tickers = [ticker for ticker, _ in pairs]
    for ticker_batch in _chunks(materialize_tickers, MATERIALIZE_TICKER_BATCH_SIZE):
        try:
            result.materialized += await materialize_asset_dividends(
                db=db,
                tickers=ticker_batch,
                commit=True,
            )
        except Exception as exc:
            await db.rollback()
            label = f"{ticker_batch[0]}..{ticker_batch[-1]}"
            logger.error(
                "[proventos_daily] falha na materializacao do lote %s (%s tickers): %s",
                label,
                len(ticker_batch),
                exc,
            )
            result.errors.append(f"materialize[{label}]: {exc}")

    result.portfolios_invalidated = await _invalidate_affected_portfolios(
        db,
        materialize_tickers,
    )

    logger.info(
        "[proventos_daily] concluido: scanned=%s synced=%s failed=%s skipped=%s historical=%s materialized=%s portfolios_invalidated=%s errors=%s",
        result.assets_scanned,
        result.assets_synced,
        result.assets_failed,
        result.assets_skipped,
        result.historical_events,
        result.materialized,
        result.portfolios_invalidated,
        len(result.errors),
    )
    return result
