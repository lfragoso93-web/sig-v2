"""
price_history_backfill_service.py

Responsável pelo preenchimento inicial (one-time) e incremental diário
do histórico de preços na tabela asset_prices.

Fluxo de boot:
  run_initial_backfill()
    ├── Verifica se asset_prices está vazia
    ├── Se vazia → backfill completo de 10 anos para todos os assets
    └── Se não vazia → só retorna (incremental fica a cargo do scheduler)

Fluxo incremental (scheduler diário):
  run_incremental_update()
    └── Para cada asset ativo, busca apenas o delta desde o last_ts
        → no máximo 1 request por ativo por dia

Ordem de prioridade no backfill inicial:
  1. ACAO   → maior cobertura BRAPI, sem fallback yfinance
  2. FII    → endpoint dedicado BRAPI /v2/fii/historical
  3. ETF_NACIONAL
  4. BDR    → deixado por último: maioria sem histórico na BRAPI,
               aciona fallback yfinance e sofre rate-limit
  5. demais tipos

Estrategia de busca por tipo de ativo:
  FII                        → BRAPI /v2/fii/historical
  ACAO, ETF_NACIONAL, BDR   → BRAPI /v2/stocks/historical
  STOCK, ETF_INTERNACIONAL   → Alpha Vantage → fallback yfinance
  CRIPTO                     → BRAPI /v2/crypto (snapshot)
  NO_QUOTE_TYPES             → ignorado

Rate limiting:
  - Ativos BR processados sequencialmente com _BRAPI_DELAY entre cada um
  - yfinance usa _YF_MIN_INTERVAL via throttle existente
  - Alpha Vantage usa token bucket (4 req/min) via rate_limiter
"""
import asyncio
import logging
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, case, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import NO_QUOTE_TYPES, INTL_TYPES
from app.core.database import AsyncSessionLocal
from app.integrations.brapi import (
    fetch_stocks_historical_v2,
    fetch_fii_historical_v2,
    is_known_by_brapi,
)
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

logger = logging.getLogger(__name__)

# Anos de histórico a buscar no backfill inicial
BACKFILL_YEARS = 10

# Delay entre cada ativo no backfill.
# 1.2s → ~50 ativos/min, abaixo do limite do yfinance como fallback.
_BRAPI_DELAY = 1.2  # segundos

# Ordem de prioridade de tipos no backfill: tipos com melhor cobertura BRAPI primeiro.
# BDR fica por último pois a maioria cai no fallback yfinance (rate-limit mais sensível).
_TYPE_PRIORITY: dict[str, int] = {
    "acao":          1,
    "fii":           2,
    "etf_nacional":  3,
    "etf_internacional": 4,
    "stock":         5,
    "bdr":           6,
    "cripto":        7,
}

# Flag global para evitar que dois backfills rodem simultaneamente
_backfill_running = False


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _date_from_years(years: int) -> str:
    return (date.today() - timedelta(days=years * 365)).isoformat()


async def _count_prices(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(AssetPrice))
    return result.scalar_one() or 0


async def _last_saved_ts(db: AsyncSession, asset_id: int) -> Optional[datetime]:
    result = await db.execute(
        select(func.max(AssetPrice.timestamp)).where(AssetPrice.asset_id == asset_id)
    )
    return result.scalar_one_or_none()


async def _upsert_prices(
    db: AsyncSession,
    asset_id: int,
    rows: list[tuple[datetime, float]],
    source: str,
) -> int:
    if not rows:
        return 0
    inserted = 0
    for ts, close in rows:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        stmt = (
            pg_insert(AssetPrice)
            .values(
                asset_id=asset_id,
                timestamp=ts,
                close=Decimal(str(round(close, 8))),
                source=source,
            )
            .on_conflict_do_nothing(constraint="uq_price_asset_timestamp")
        )
        await db.execute(stmt)
        inserted += 1
    await db.commit()
    return inserted


async def _update_asset_last_price(
    db: AsyncSession,
    asset: Asset,
    rows: list[tuple[datetime, float]],
) -> None:
    if not rows:
        return
    latest_close = rows[-1][1]
    asset.last_price = Decimal(str(round(latest_close, 8)))
    asset.last_price_updated_at = _now_utc()
    await db.commit()


def _sort_key(asset: Asset) -> tuple[int, str]:
    """Ordena por prioridade de tipo, depois por ticker alfabético."""
    priority = _TYPE_PRIORITY.get(asset.asset_type.lower() if asset.asset_type else "", 99)
    return (priority, asset.ticker or "")


# ---------------------------------------------------------------------------
# Busca de histórico por tipo
# ---------------------------------------------------------------------------

async def _fetch_br_history(
    ticker: str,
    asset_type: AssetType,
    date_from: str,
    date_to: str,
) -> tuple[list[tuple[datetime, float]], str]:
    from app.core.asset_types import yf_ticker
    from app.services.price_history_service import _fetch_yf_history

    brapi_known = await is_known_by_brapi(ticker)

    if brapi_known:
        try:
            if asset_type == AssetType.FII:
                rows = await fetch_fii_historical_v2(
                    ticker=ticker, date_from=date_from, date_to=date_to
                )
                if rows:
                    return rows, "brapi_v2_fii"
            else:
                rows = await fetch_stocks_historical_v2(
                    ticker=ticker, date_from=date_from, date_to=date_to
                )
                if rows:
                    return rows, "brapi_v2_stocks"
        except Exception as e:
            logger.warning("[Backfill] BRAPI v2 erro para %s: %s", ticker, e)

    # Fallback yfinance
    try:
        days = (date.today() - date.fromisoformat(date_from)).days + 1
        rows = await _fetch_yf_history(ticker, asset_type, days)
        if rows:
            return rows, "yfinance_fallback"
    except Exception as e:
        logger.warning("[Backfill] yfinance erro para %s: %s", ticker, e)

    return [], ""


async def _fetch_intl_history(
    ticker: str,
    asset_type: AssetType,
    days: int,
) -> tuple[list[tuple[datetime, float]], str]:
    from app.services.price_history_service import _fetch_yf_history

    try:
        from app.core.rate_limiter import alpha_vantage_limiter
        from app.integrations.alpha_vantage import fetch_daily_history
        await alpha_vantage_limiter.acquire()
        rows = await fetch_daily_history(ticker, days)
        if rows:
            return rows, "alpha_vantage"
    except Exception as e:
        logger.warning("[Backfill] Alpha Vantage erro para %s: %s", ticker, e)

    try:
        rows = await _fetch_yf_history(ticker, asset_type, days)
        if rows:
            return rows, "yfinance_fallback"
    except Exception as e:
        logger.warning("[Backfill] yfinance erro para %s: %s", ticker, e)

    return [], ""


# ---------------------------------------------------------------------------
# Backfill de um único ativo
# ---------------------------------------------------------------------------

async def backfill_single_asset(
    db: AsyncSession,
    asset: Asset,
    date_from: str,
    date_to: str,
    force: bool = False,
) -> int:
    if asset.asset_type in NO_QUOTE_TYPES:
        return 0

    if not force:
        first_ts_result = await db.execute(
            select(func.min(AssetPrice.timestamp)).where(
                AssetPrice.asset_id == asset.id
            )
        )
        first_ts = first_ts_result.scalar_one_or_none()
        if first_ts:
            cutoff = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
            if first_ts <= cutoff + timedelta(days=5):
                logger.debug(
                    "[Backfill] %s já tem histórico desde %s — pulando",
                    asset.ticker, first_ts.date()
                )
                return 0

    is_intl = asset.asset_type in INTL_TYPES
    days = (date.today() - date.fromisoformat(date_from)).days + 1

    if is_intl:
        rows, source = await _fetch_intl_history(asset.ticker, asset.asset_type, days)
    else:
        rows, source = await _fetch_br_history(
            asset.ticker, asset.asset_type, date_from, date_to
        )

    if not rows:
        logger.info("[Backfill] %s sem histórico disponível", asset.ticker)
        return 0

    inserted = await _upsert_prices(db, asset.id, rows, source)
    await _update_asset_last_price(db, asset, rows)
    logger.info(
        "[Backfill] %s: %d registros inseridos (source=%s)",
        asset.ticker, inserted, source
    )
    return inserted


# ---------------------------------------------------------------------------
# Backfill inicial completo (one-time na subida)
# ---------------------------------------------------------------------------

async def run_initial_backfill(force: bool = False) -> None:
    """
    Executa o backfill histórico completo de 10 anos para todos os assets.

    Só roda se asset_prices estiver vazia (ou force=True).
    Se asset_prices já tiver dados mas não for force, retorna imediatamente.

    Ordem: ACAO → FII → ETF_NACIONAL → ETF_INTERNACIONAL → STOCK → BDR → outros.
    BDRs ficam por último pois a maioria cai no fallback yfinance.

    Ativos já com histórico cobrindo o período são pulados automaticamente
    (sem request à API), permitindo retomar de onde parou após restart.
    """
    global _backfill_running
    if _backfill_running:
        logger.info("[Backfill] já em execução — ignorando nova chamada")
        return

    _backfill_running = True
    try:
        async with AsyncSessionLocal() as db:
            if not force:
                count = await _count_prices(db)
                if count > 0:
                    logger.info(
                        "[Backfill] asset_prices já contém %d registros — "
                        "pulando backfill inicial", count
                    )
                    return

            result = await db.execute(
                select(Asset)
                .where(Asset.asset_type.notin_(list(NO_QUOTE_TYPES)))
            )
            assets = result.scalars().all()

        if not assets:
            logger.warning("[Backfill] nenhum asset encontrado — execute o seed primeiro")
            return

        # Ordena: tipos prioritários primeiro, BDR por último
        assets_sorted = sorted(assets, key=_sort_key)

        date_from = _date_from_years(BACKFILL_YEARS)
        date_to   = date.today().isoformat()
        total     = len(assets_sorted)
        done      = 0
        errors    = 0
        skipped   = 0

        # Log contagem por tipo
        type_counts: dict[str, int] = {}
        for a in assets_sorted:
            type_counts[a.asset_type] = type_counts.get(a.asset_type, 0) + 1
        logger.info(
            "[Backfill] iniciando backfill de %d ativos (%s a %s) | por tipo: %s",
            total, date_from, date_to, type_counts
        )

        for asset in assets_sorted:
            try:
                async with AsyncSessionLocal() as db:
                    inserted = await backfill_single_asset(
                        db, asset, date_from, date_to, force=force
                    )
                if inserted == 0:
                    skipped += 1
                done += 1
                if done % 50 == 0:
                    logger.info(
                        "[Backfill] progresso: %d/%d processados (%d com dados, %d sem/já ok)",
                        done, total, done - skipped, skipped
                    )
            except Exception as e:
                errors += 1
                logger.error("[Backfill] erro em %s: %s", asset.ticker, e)

            await asyncio.sleep(_BRAPI_DELAY)

        logger.info(
            "[Backfill] concluído: %d/%d ativos | %d com dados | %d sem histórico | %d erros",
            done, total, done - skipped, skipped, errors
        )

    finally:
        _backfill_running = False


# ---------------------------------------------------------------------------
# Atualização incremental diária (scheduler)
# ---------------------------------------------------------------------------

async def run_incremental_update() -> None:
    """
    Atualiza apenas o delta desde o último registro de cada ativo.
    Chamado pelo scheduler diariamente após o fechamento do mercado.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Asset)
            .where(Asset.asset_type.notin_(list(NO_QUOTE_TYPES)))
            .order_by(Asset.ticker)
        )
        assets = result.scalars().all()

    date_to   = date.today().isoformat()
    updated   = 0
    skipped   = 0

    for asset in assets:
        try:
            async with AsyncSessionLocal() as db:
                last_ts = await _last_saved_ts(db, asset.id)

                if last_ts:
                    delta_days = (_now_utc() - last_ts).days
                    if delta_days < 1:
                        skipped += 1
                        continue
                    delta_days = min(delta_days, 7)
                    date_from = (
                        date.today() - timedelta(days=delta_days + 1)
                    ).isoformat()
                else:
                    date_from = (date.today() - timedelta(days=30)).isoformat()

                inserted = await backfill_single_asset(
                    db, asset, date_from, date_to, force=True
                )
                if inserted:
                    updated += 1

        except Exception as e:
            logger.error("[Incremental] erro em %s: %s", asset.ticker, e)

        await asyncio.sleep(_BRAPI_DELAY)

    logger.info(
        "[Incremental] concluído: %d atualizados, %d já em dia",
        updated, skipped
    )


# ---------------------------------------------------------------------------
# Status do backfill (para endpoint de admin/health)
# ---------------------------------------------------------------------------

async def get_backfill_status() -> dict:
    async with AsyncSessionLocal() as db:
        total_prices = await _count_prices(db)

        assets_result = await db.execute(
            select(func.count()).select_from(Asset)
            .where(Asset.asset_type.notin_(list(NO_QUOTE_TYPES)))
        )
        total_assets = assets_result.scalar_one() or 0

        assets_with_prices_result = await db.execute(
            select(func.count(func.distinct(AssetPrice.asset_id)))
        )
        assets_with_prices = assets_with_prices_result.scalar_one() or 0

        oldest_result = await db.execute(select(func.min(AssetPrice.timestamp)))
        oldest = oldest_result.scalar_one_or_none()

        newest_result = await db.execute(select(func.max(AssetPrice.timestamp)))
        newest = newest_result.scalar_one_or_none()

    return {
        "running": _backfill_running,
        "total_price_records": total_prices,
        "total_assets": total_assets,
        "assets_with_prices": assets_with_prices,
        "coverage_pct": round(assets_with_prices / total_assets * 100, 1) if total_assets else 0,
        "oldest_record": oldest.date().isoformat() if oldest else None,
        "newest_record": newest.date().isoformat() if newest else None,
    }
