"""
Histórico de preços do Tesouro Direto.

Usa o catálogo persistido em assets (asset_type=TESOURO_DIRETO) e o endpoint
BRAPI /api/v2/treasury/indicators/history para gravar preços em asset_prices.

Fonte salva em asset_prices.source: brapi_treasury.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.integrations.brapi_treasury import fetch_treasury_history, fetch_treasury_prices
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

logger = logging.getLogger(__name__)

SOURCE = "brapi_treasury"
DEFAULT_HISTORY_YEARS = 10
_INCREMENTAL_LOOKBACK_DAYS = 10
_TREASURY_HISTORY_CHUNK = 20

_running = False


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _default_start_date() -> date:
    return date.today() - timedelta(days=DEFAULT_HISTORY_YEARS * 365)


async def _treasury_assets(db: AsyncSession) -> list[Asset]:
    result = await db.execute(
        select(Asset)
        .where(Asset.asset_type == AssetType.TESOURO_DIRETO.value)
        .order_by(Asset.ticker.asc())
    )
    return list(result.scalars().all())


async def _last_saved_date(db: AsyncSession, asset_id: int) -> Optional[date]:
    result = await db.execute(
        select(func.max(AssetPrice.timestamp)).where(AssetPrice.asset_id == asset_id)
    )
    last_ts = result.scalar_one_or_none()
    if not last_ts:
        return None
    return last_ts.date()


async def _upsert_price_rows(
    db: AsyncSession,
    asset: Asset,
    rows: list[tuple[datetime, float]],
) -> int:
    if not rows:
        return 0

    inserted_or_updated = 0
    latest_ts: Optional[datetime] = None
    latest_close: Optional[float] = None

    for ts, close in rows:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        value = Decimal(str(round(close, 8)))
        stmt = (
            pg_insert(AssetPrice)
            .values(
                asset_id=asset.id,
                timestamp=ts,
                close=value,
                source=SOURCE,
            )
            .on_conflict_do_update(
                constraint="uq_price_asset_timestamp",
                set_={
                    "close": value,
                    "source": SOURCE,
                },
            )
        )
        await db.execute(stmt)
        inserted_or_updated += 1
        if latest_ts is None or ts > latest_ts:
            latest_ts = ts
            latest_close = close

    if latest_close is not None:
        asset.last_price = Decimal(str(round(latest_close, 8)))
        asset.last_price_updated_at = _now_utc()

    return inserted_or_updated


async def import_treasury_price_history(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    only_missing: bool = True,
    commit: bool = True,
) -> dict[str, int]:
    """
    Importa histórico de Tesouro para asset_prices.

    only_missing=True:
      - se o título já tem histórico, atualiza somente uma janela recente;
      - se não tem, busca desde DEFAULT_HISTORY_YEARS.
    """
    assets = await _treasury_assets(db)
    if not assets:
        logger.info("[treasury_history] nenhum título TESOURO_DIRETO em assets")
        return {}

    today = end_date or date.today()
    stats: dict[str, int] = {}

    for i in range(0, len(assets), _TREASURY_HISTORY_CHUNK):
        chunk = assets[i:i + _TREASURY_HISTORY_CHUNK]
        symbol_dates: dict[str, tuple[date, date]] = {}
        assets_by_symbol: dict[str, Asset] = {}

        for asset in chunk:
            symbol = str(asset.ticker or "").strip().lower()
            if not symbol:
                continue

            fetch_from = start_date or _default_start_date()
            if only_missing:
                last_date = await _last_saved_date(db, asset.id)
                if last_date:
                    fetch_from = max(last_date - timedelta(days=2), today - timedelta(days=_INCREMENTAL_LOOKBACK_DAYS))

            if fetch_from > today:
                stats[symbol] = 0
                continue

            symbol_dates[symbol] = (fetch_from, today)
            assets_by_symbol[symbol] = asset

        # A BRAPI aceita várias symbols, mas start/end são compartilhados por chamada.
        # Para preservar incremental correto por título, agrupamos por janela.
        windows: dict[tuple[date, date], list[str]] = {}
        for symbol, window in symbol_dates.items():
            windows.setdefault(window, []).append(symbol)

        for (window_start, window_end), symbols in windows.items():
            try:
                history = await fetch_treasury_history(symbols, window_start, window_end)
            except Exception as exc:
                logger.warning(
                    "[treasury_history] falha ao buscar histórico %s-%s para %s: %s",
                    window_start,
                    window_end,
                    symbols,
                    exc,
                )
                continue

            for symbol in symbols:
                asset = assets_by_symbol[symbol]
                rows = history.get(symbol, [])
                if not rows:
                    stats[symbol] = 0
                    continue
                count = await _upsert_price_rows(db, asset, rows)
                stats[symbol] = stats.get(symbol, 0) + count

    if commit:
        await db.commit()

    logger.info("[treasury_history] importação concluída: %s", stats)
    return stats


async def import_missing_treasury_price_history() -> dict[str, int]:
    """Entrada usada no boot para backfill inicial/incremental leve."""
    global _running
    if _running:
        logger.info("[treasury_history] importação já em execução — ignorando")
        return {}

    _running = True
    try:
        async with AsyncSessionLocal() as db:
            return await import_treasury_price_history(db, only_missing=True)
    finally:
        _running = False


async def update_treasury_latest_prices(db: AsyncSession, commit: bool = True) -> dict[str, float]:
    """
    Atualiza apenas o snapshot atual dos títulos do Tesouro em assets.last_price.
    Útil quando o endpoint de histórico não retorna dado para o dia corrente.
    """
    assets = await _treasury_assets(db)
    symbols = [str(asset.ticker).lower() for asset in assets if asset.ticker]
    if not symbols:
        return {}

    prices = await fetch_treasury_prices(symbols)
    by_symbol = {str(asset.ticker).lower(): asset for asset in assets if asset.ticker}
    now = _now_utc()

    for symbol, price in prices.items():
        asset = by_symbol.get(symbol)
        if not asset:
            continue
        asset.last_price = Decimal(str(round(price, 8)))
        asset.last_price_updated_at = now

    if commit:
        await db.commit()

    logger.info("[treasury_history] snapshot atual Tesouro atualizado: %d títulos", len(prices))
    return prices
