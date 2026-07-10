"""
price_history_service.py

Apos a migração para backfill pre-populado, este servico e responsavel por:

  1. get_price_at_date   — leitura pura do banco, nunca chama API
  2. get_price_history   — leitura pura do banco, nunca chama API
  3. persist_daily_prices — incremental simples (delta desde last_ts)
                           Usado pelo scheduler e pelo asset_onboarding.

O backfill inicial de 10 anos e responsabilidade de:
  app/services/price_history_backfill_service.py

Regra de negocio para get_price_at_date:
  Busca o fechamento mais recente disponivel no intervalo
  [target_date - 5 dias, target_date + 1 dia].
  Isso cobre: finais de semana, feriados e dias sem pregao.
  Se nao encontrar, retorna None e loga warning — nunca dispara API.

Rate limiting yfinance (threading.Lock - nivel de thread):
  _yf_thread_lock garante que apenas uma thread execute yfinance de cada vez.
  _YF_MIN_INTERVAL (12s) adiciona pausa minima para evitar 429.

Fallback de snapshot para INTL (YFRateLimitError):
  Quando tanto Alpha Vantage quanto yfinance falham para ativos INTL
  (IVV, NVDA, INTR, TFLO etc.), persist_daily_prices tenta obter o
  preco atual via quotes_service._mem_get_stale() (cache L2 em memoria)
  ou Asset.last_price no banco. Isso garante que pelo menos o preco mais
  recente conhecido seja persistido como AssetPrice, evitando que
  get_price_at_date retorne None e cause zeros no frontend.
"""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable, Optional

import yfinance as yf
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import NO_QUOTE_TYPES, INTL_TYPES, yf_ticker
from app.integrations.brapi import (
    fetch_stocks_historical_v2,
    fetch_fii_historical_v2,
    is_known_by_brapi,
)
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

logger = logging.getLogger(__name__)

# -- yfinance thread pool e rate limiter --------------------------------------
_YF_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="yfinance_hist")
_yf_thread_lock = threading.Lock()
_YF_MIN_INTERVAL: float = 12.0
_yf_last_call: list[float] = [0.0]

# -- Cooldown de persistencia (para o incremental do scheduler) ---------------
# Estrutura: {ticker: expires_at (monotonic)}
PERSIST_COOLDOWN_SECONDS: float = 1800.0  # 30 minutos
_persist_cooldown: dict[str, float] = {}
_cooldown_lock = threading.Lock()


def _is_in_cooldown(ticker: str) -> bool:
    with _cooldown_lock:
        exp = _persist_cooldown.get(ticker)
        return exp is not None and time.monotonic() < exp


def _set_cooldown(ticker: str) -> None:
    with _cooldown_lock:
        _persist_cooldown[ticker] = time.monotonic() + PERSIST_COOLDOWN_SECONDS


def _clear_cooldown(ticker: str) -> None:
    with _cooldown_lock:
        _persist_cooldown.pop(ticker, None)


# -- Tipos BRAPI v2 -----------------------------------------------------------
_FII_V2_TYPES    = {AssetType.FII}
_STOCKS_V2_TYPES = {AssetType.ACAO, AssetType.ETF_NACIONAL, AssetType.BDR}

_BR_CLOSE_HOUR_UTC = 21


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_date_utc(date_str: str) -> datetime:
    d = date_str[:10]
    return datetime(int(d[:4]), int(d[5:7]), int(d[8:10]), tzinfo=timezone.utc)


async def _run_yf_with_throttle(fn: Callable, *args):
    import asyncio
    loop = asyncio.get_event_loop()

    def _throttled():
        with _yf_thread_lock:
            elapsed = time.monotonic() - _yf_last_call[0]
            if elapsed < _YF_MIN_INTERVAL:
                time.sleep(_YF_MIN_INTERVAL - elapsed)
            try:
                return fn(*args)
            finally:
                _yf_last_call[0] = time.monotonic()

    return await loop.run_in_executor(_YF_EXECUTOR, _throttled)


async def _upsert_price(
    db: AsyncSession,
    asset_id: int,
    timestamp: datetime,
    close: float,
    source: str = "brapi_v2",
) -> None:
    stmt = (
        pg_insert(AssetPrice)
        .values(
            asset_id=asset_id,
            timestamp=timestamp,
            close=Decimal(str(round(close, 8))),
            source=source,
        )
        .on_conflict_do_nothing(constraint="uq_price_asset_timestamp")
    )
    await db.execute(stmt)


async def _get_or_create_asset(db: AsyncSession, ticker: str, asset_type: AssetType) -> Asset:
    result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    asset = result.scalar_one_or_none()
    if asset is None:
        asset = Asset(ticker=ticker, name=ticker, asset_type=asset_type)
        db.add(asset)
        await db.flush()
    return asset


async def _last_saved_ts(db: AsyncSession, asset_id: int) -> Optional[datetime]:
    result = await db.execute(
        select(func.max(AssetPrice.timestamp)).where(AssetPrice.asset_id == asset_id)
    )
    return result.scalar_one_or_none()


def _fetch_yf_history_sync(yf_sym: str, days: int) -> list[tuple[datetime, float]]:
    try:
        from datetime import date as _date
        tk = yf.Ticker(yf_sym)
        start_date = _date.today() - timedelta(days=days)
        end_date   = _date.today() + timedelta(days=1)
        hist = tk.history(
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval="1d",
            auto_adjust=True,
        )
        if hist.empty:
            return []
        rows = []
        for ts, row in hist.iterrows():
            close = float(row["Close"])
            if close and close > 0:
                dt = ts.to_pydatetime()
                dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
                rows.append((dt, close))
        return rows
    except Exception as e:
        logger.warning("[PriceHistory] yfinance error %s: %s", yf_sym, e)
        return []


async def _fetch_yf_history(
    ticker: str,
    asset_type: AssetType,
    days: int,
) -> list[tuple[datetime, float]]:
    sym = yf_ticker(ticker, asset_type)
    return await _run_yf_with_throttle(_fetch_yf_history_sync, sym, days)


async def _intl_stale_snapshot(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
) -> list[tuple[datetime, float]]:
    """
    Ultimo recurso para ativos INTL quando AV e yfinance falham (rate limit).

    Tenta obter um preco conhecido em duas camadas:
      1. quotes_service._mem_get_stale() — cache L2 em memoria (mesmo expirado)
      2. Asset.last_price no banco        — ultimo preco salvo

    Se encontrar, persiste como AssetPrice com source='stale_snapshot' para
    garantir que get_price_at_date nao retorne None e o frontend nao mostre zeros.
    """
    try:
        from app.services.quotes_service import _mem_get_stale
        stale_price = _mem_get_stale(ticker)
        if stale_price and stale_price > 0:
            logger.warning(
                "[PriceHistory] INTL %s — AV+YF falharam, usando mem_cache stale: %.4f",
                ticker, stale_price,
            )
            ts = _now_utc().replace(hour=20, minute=0, second=0, microsecond=0)
            return [(ts, stale_price)]
    except Exception as e:
        logger.debug("[PriceHistory] _mem_get_stale indisponivel para %s: %s", ticker, e)

    try:
        result = await db.execute(
            select(Asset.last_price, Asset.last_price_updated_at)
            .where(Asset.ticker == ticker)
        )
        row = result.first()
        if row and row.last_price and float(row.last_price) > 0:
            price = float(row.last_price)
            ts = row.last_price_updated_at or _now_utc()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            logger.warning(
                "[PriceHistory] INTL %s — AV+YF falharam, usando last_price do banco: %.4f (de %s)",
                ticker, price, ts.date(),
            )
            return [(ts, price)]
    except Exception as e:
        logger.warning("[PriceHistory] _intl_stale_snapshot banco falhou para %s: %s", ticker, e)

    logger.error(
        "[PriceHistory] INTL %s — sem preco em nenhuma camada (AV, YF, mem_cache, banco)",
        ticker,
    )
    return []


# ---------------------------------------------------------------------------
# persist_daily_prices — incremental simples
# ---------------------------------------------------------------------------

async def persist_daily_prices(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    days_back: int = 30,
    force: bool = False
) -> int:
    """
    Busca e persiste apenas o delta desde o last_ts (incremental simples).

    Nao faz backfill historico completo — isso e responsabilidade de
    price_history_backfill_service.run_initial_backfill().
    """
    if asset_type in NO_QUOTE_TYPES:
        return 0

    if not force and _is_in_cooldown(ticker):
        logger.debug("[PriceHistory] %s em cooldown — pulando", ticker)
        return 0

    if force:
        _clear_cooldown(ticker)

    asset = await _get_or_create_asset(db, ticker, asset_type)
    last_ts = await _last_saved_ts(db, asset.id)

    if last_ts:
        delta = (_now_utc() - last_ts).days
        if not force and delta < 1:
            _set_cooldown(ticker)
            return 0
        days_back = max(min(delta + 1, days_back), 2)

    date_to   = _now_utc().date().isoformat()
    date_from = (_now_utc().date() - timedelta(days=days_back)).isoformat()

    rows: list[tuple[datetime, float]] = []
    source = ""
    is_intl = asset_type in INTL_TYPES

    if is_intl:
        try:
            from app.core.rate_limiter import alpha_vantage_limiter
            from app.integrations.alpha_vantage import fetch_daily_history
            await alpha_vantage_limiter.acquire()
            rows = await fetch_daily_history(ticker, days_back)
            source = "alpha_vantage"
        except Exception as e:
            logger.warning("[PriceHistory] Alpha Vantage excecao para %s: %s", ticker, e)

        if not rows:
            try:
                rows = await _fetch_yf_history(ticker, asset_type, days_back)
                source = "yfinance_fallback"
            except Exception as e:
                logger.warning("[PriceHistory] yfinance excecao para %s: %s", ticker, e)

        if not rows:
            rows = await _intl_stale_snapshot(db, ticker, asset_type)
            if rows:
                source = "stale_snapshot"
    else:
        brapi_known = await is_known_by_brapi(ticker)
        if brapi_known:
            try:
                if asset_type == AssetType.FII:
                    rows = await fetch_fii_historical_v2(ticker=ticker, date_from=date_from, date_to=date_to)
                    source = "brapi_v2_fii"
                else:
                    rows = await fetch_stocks_historical_v2(ticker=ticker, date_from=date_from, date_to=date_to)
                    source = "brapi_v2_stocks"
            except Exception as e:
                logger.warning("[PriceHistory] BRAPI v2 excecao para %s: %s", ticker, e)

        # Para ativos BR conhecidos, não fazemos fallback para yfinance no
        # incremental operacional. Se a janela BRAPI vier vazia, usamos snapshot
        # BRAPI abaixo. Isso evita rate limit e ruído diário do yfinance.
        if not rows and not brapi_known:
            try:
                rows = await _fetch_yf_history(ticker, asset_type, days_back)
                source = "yfinance_fallback"
            except Exception as e:
                logger.warning("[PriceHistory] yfinance excecao para %s: %s", ticker, e)

    if not rows and not is_intl:
        try:
            from app.integrations.brapi import fetch_quotes as brapi_fetch_quotes
            result = await brapi_fetch_quotes([ticker])
            price = result.get(ticker)
            if price:
                ts = _now_utc().replace(hour=_BR_CLOSE_HOUR_UTC, minute=0, second=0, microsecond=0)
                rows = [(ts, price)]
                source = "brapi_snapshot"
        except Exception as e:
            logger.warning("[PriceHistory] snapshot fallback falhou para %s: %s", ticker, e)

    inserted = 0
    for ts, close in rows:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        await _upsert_price(db, asset.id, ts, close, source)
        inserted += 1

    if inserted:
        latest_close = rows[-1][1]
        asset.last_price = Decimal(str(round(latest_close, 8)))
        asset.last_price_updated_at = _now_utc()

    await db.commit()
    logger.info(
        "[PriceHistory] %s: %d registros persistidos (source=%s, force=%s)",
        ticker, inserted, source, force
    )
    _set_cooldown(ticker)
    return inserted


# ---------------------------------------------------------------------------
# get_price_at_date — SOMENTE LEITURA DO BANCO
# ---------------------------------------------------------------------------

async def get_price_at_date(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    target_date: str,
) -> Optional[float]:
    """
    Retorna o preço de fechamento mais recente disponivel ate target_date.

    Busca no intervalo [target_date - 5 dias, target_date + 1 dia] para
    cobrir finais de semana, feriados e dias sem pregao.

    NUNCA chama API. Se nao houver dado no banco, retorna None e loga warning.
    O backfill pre-populado garante que os dados estejam disponiveis.
    """
    ref   = _parse_date_utc(target_date)
    since = ref - timedelta(days=5)
    until = ref + timedelta(hours=23, minutes=59, seconds=59)

    asset_result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    asset = asset_result.scalar_one_or_none()

    if not asset:
        logger.warning(
            "[PriceHistory] get_price_at_date: asset %s nao encontrado no banco",
            ticker
        )
        return None

    rows = await db.execute(
        select(AssetPrice)
        .where(
            AssetPrice.asset_id == asset.id,
            AssetPrice.timestamp >= since,
            AssetPrice.timestamp <= until,
        )
        .order_by(AssetPrice.timestamp.desc())
        .limit(1)
    )
    price_row = rows.scalar_one_or_none()

    if not price_row:
        logger.warning("[PriceHistory] preco nao encontrado para %s em %s", ticker, target_date)
        return None

    return float(price_row.close)


async def get_prices_at_date_batch(
    db: AsyncSession,
    tickers_with_types: list[tuple[str, AssetType]],
    target_date: str,
) -> dict[str, float]:
    """
    Retorna fechamento por ticker em lote para uma data de referencia.

    Mantem a mesma semantica de get_price_at_date: busca o preco mais recente
    disponivel na janela [target_date - 5 dias, target_date + 1 dia], sem
    disparar APIs externas. Tickers sem preco retornam ausentes do dict.
    """
    if not tickers_with_types:
        return {}

    ref = _parse_date_utc(target_date)
    since = ref - timedelta(days=5)
    until = ref + timedelta(hours=23, minutes=59, seconds=59)
    tickers = [ticker.upper() for ticker, _ in tickers_with_types]

    assets_result = await db.execute(
        select(Asset.id, Asset.ticker)
        .where(Asset.ticker.in_(tickers))
    )
    asset_rows = assets_result.all()
    asset_id_to_ticker = {row.id: row.ticker.upper() for row in asset_rows}

    if not asset_id_to_ticker:
        for ticker in tickers:
            logger.warning(
                "[PriceHistory] get_prices_at_date_batch: asset %s nao encontrado no banco",
                ticker,
            )
        return {}

    rows_result = await db.execute(
        select(AssetPrice)
        .where(
            AssetPrice.asset_id.in_(asset_id_to_ticker.keys()),
            AssetPrice.timestamp >= since,
            AssetPrice.timestamp <= until,
        )
        .order_by(AssetPrice.asset_id.asc(), AssetPrice.timestamp.desc())
    )

    prices: dict[str, float] = {}
    for price_row in rows_result.scalars().all():
        ticker = asset_id_to_ticker.get(price_row.asset_id)
        if ticker and ticker not in prices:
            prices[ticker] = float(price_row.close)

    missing = [ticker for ticker in tickers if ticker not in prices]
    for ticker in missing:
        logger.warning("[PriceHistory] preco nao encontrado para %s em %s", ticker, target_date)

    return prices


async def get_price_history(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    days: int = 365,
) -> list[dict]:
    cutoff = _now_utc() - timedelta(days=days)
    asset_result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    asset = asset_result.scalar_one_or_none()
    if not asset:
        return []

    rows = await db.execute(
        select(AssetPrice)
        .where(AssetPrice.asset_id == asset.id, AssetPrice.timestamp >= cutoff)
        .order_by(AssetPrice.timestamp.asc())
    )
    return [
        {"timestamp": r.timestamp, "close": float(r.close), "source": r.source}
        for r in rows.scalars().all()
    ]
