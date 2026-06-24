"""
Servico de historico de precos.

Estrategia de busca (por camadas):

  Ativos BR (ACAO, FII, ETF_NACIONAL, BDR, CRIPTO):
    L0 - Validacao BRAPI: verifica se o ticker e conhecido pela BRAPI via
         cache em memoria (populado pelo seed via /api/v2/tickers).
         Tickers desconhecidos pulam direto para yfinance, evitando
         400 em massa no endpoint legado.
    L1 - BRAPI v2:
         FII -> /api/v2/fii/historical
         demais -> /api/v2/stocks/historical
    L2 - BRAPI legado /quote/{ticker}?range=custom
    L3 - yfinance (fallback final)
    L4 - Snapshot BRAPI (ultimo recurso)

  Ativos INTL (STOCK, ETF_INTERNACIONAL):
    L1 - Alpha Vantage TIME_SERIES_DAILY (primario real para INTL)
    L2 - yfinance (fallback)
    L3 - Snapshot BRAPI (ultimo recurso)
    Nota: BRAPI v2 e completamente ignorado para INTL (sempre 404/500).

Rate limiting yfinance (threading.Lock - nivel de thread):
  _yf_thread_lock garante que apenas uma thread execute yfinance de cada vez.
  _YF_MIN_INTERVAL (8s) adiciona pausa minima para evitar 429 Too Many Requests.

Lock por ticker (_ticker_locks):
  Evita que multiplos endpoints (performance, portfolio, summary) disparem
  persist_daily_prices para o mesmo ticker simultaneamente.

Rate limiting Alpha Vantage:
  alpha_vantage_limiter (TokenBucket, 4 req/min) em core/rate_limiter.py.
"""
import asyncio
import logging
import threading
import time
from collections import defaultdict
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
    fetch_price_history as brapi_fetch_history_legacy,
    fetch_stocks_historical_v2,
    fetch_fii_historical_v2,
    is_known_by_brapi,
)
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

logger = logging.getLogger(__name__)

# ── yfinance thread pool e rate limiter ──────────────────────────────────────
_YF_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="yfinance_hist")
_yf_thread_lock = threading.Lock()
_YF_MIN_INTERVAL: float = 8.0
_yf_last_call: list[float] = [0.0]

# ── Lock por ticker ───────────────────────────────────────────────────────────
_ticker_locks: dict[str, asyncio.Lock] = {}
_ticker_locks_mutex = threading.Lock()


def _get_ticker_lock(ticker: str) -> asyncio.Lock:
    with _ticker_locks_mutex:
        if ticker not in _ticker_locks:
            _ticker_locks[ticker] = asyncio.Lock()
        return _ticker_locks[ticker]


# ── Tipos BRAPI v2 ────────────────────────────────────────────────────────────
_FII_V2_TYPES    = {AssetType.FII}
_STOCKS_V2_TYPES = {AssetType.ACAO, AssetType.ETF_NACIONAL, AssetType.BDR}

PRICE_TTL_SECONDS  = 900
_BR_CLOSE_HOUR_UTC = 21


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_date_utc(date_str: str) -> datetime:
    d = date_str[:10]
    return datetime(int(d[:4]), int(d[5:7]), int(d[8:10]), tzinfo=timezone.utc)


async def _run_yf_with_throttle(fn: Callable, *args):
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
        tk = yf.Ticker(yf_sym)
        hist = tk.history(period=f"{days}d", interval="1d", auto_adjust=True)
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
        logger.warning(f"[PriceHistory] yfinance error {yf_sym}: {e}")
        return []


async def _fetch_yf_history(ticker: str, asset_type: AssetType, days: int) -> list[tuple[datetime, float]]:
    sym = yf_ticker(ticker, asset_type)
    return await _run_yf_with_throttle(_fetch_yf_history_sync, sym, days)


async def _fetch_av_history(ticker: str, days_back: int) -> list[tuple[datetime, float]]:
    from app.core.rate_limiter import alpha_vantage_limiter
    from app.integrations.alpha_vantage import fetch_daily_history
    await alpha_vantage_limiter.acquire()
    return await fetch_daily_history(ticker, days_back)


async def _fetch_brapi_v2(
    ticker: str,
    asset_type: AssetType,
    date_from: str,
    date_to: str,
) -> tuple[list[tuple[datetime, float]], str]:
    try:
        if asset_type in _FII_V2_TYPES:
            rows = await fetch_fii_historical_v2(ticker=ticker, date_from=date_from, date_to=date_to)
            return rows, "brapi_v2_fii"
        elif asset_type in _STOCKS_V2_TYPES:
            rows = await fetch_stocks_historical_v2(ticker=ticker, date_from=date_from, date_to=date_to)
            return rows, "brapi_v2_stocks"
    except Exception as e:
        logger.warning(f"[PriceHistory] BRAPI v2 excecao para {ticker} ({asset_type}): {e}")
    return [], ""


async def persist_daily_prices(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    days_back: int = 365,
) -> int:
    """
    Persiste historico de precos diarios para um ativo.
    Usa lock por ticker para evitar requests duplicados quando multiplos
    endpoints chamam o mesmo ticker concorrentemente.
    """
    if asset_type in NO_QUOTE_TYPES:
        logger.debug(f"[PriceHistory] {ticker} ({asset_type}) sem cotacao — ignorado")
        return 0

    lock = _get_ticker_lock(ticker)
    async with lock:
        return await _persist_daily_prices_inner(db, ticker, asset_type, days_back)


async def _persist_daily_prices_inner(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    days_back: int,
) -> int:
    asset = await _get_or_create_asset(db, ticker, asset_type)
    last_ts = await _last_saved_ts(db, asset.id)

    if last_ts:
        delta = (_now_utc() - last_ts).days
        if delta < 1:
            logger.debug(f"[PriceHistory] {ticker} banco atualizado (last={last_ts.date()}) — pulando")
            return 0
        days_back = min(days_back, max(delta + 1, 2))

    date_to   = _now_utc().date().isoformat()
    date_from = (_now_utc().date() - timedelta(days=days_back)).isoformat()

    rows:    list[tuple[datetime, float]] = []
    source:  str = ""
    is_intl = asset_type in INTL_TYPES

    if is_intl:
        # ── INTL: Alpha Vantage primeiro, yfinance como fallback ──────────────
        logger.debug(f"[PriceHistory] {ticker} (INTL) — tentando Alpha Vantage")
        try:
            rows = await _fetch_av_history(ticker, days_back)
            source = "alpha_vantage"
        except Exception as e:
            logger.warning(f"[PriceHistory] Alpha Vantage excecao para {ticker}: {e}")

        if not rows:
            logger.info(f"[PriceHistory] Alpha Vantage vazio para {ticker} — tentando yfinance")
            try:
                rows = await _fetch_yf_history(ticker, asset_type, days_back)
                source = "yfinance_fallback"
            except Exception as e:
                logger.warning(f"[PriceHistory] yfinance excecao para {ticker}: {e}")

    else:
        # ── BR: L0 validacao BRAPI → v2 → legado → yfinance ──────────────────
        # L0: verifica cache de tickers conhecidos pela BRAPI
        # (cache e populado automaticamente pelo seed via fetch_all_tickers_v2)
        brapi_known = await is_known_by_brapi(ticker)

        if brapi_known:
            # L1: BRAPI v2
            rows, source = await _fetch_brapi_v2(ticker, asset_type, date_from, date_to)

            if not rows:
                # L2: BRAPI legado — apenas para tickers conhecidos
                logger.info(f"[PriceHistory] BRAPI v2 vazio para {ticker} ({asset_type}) — tentando legado")
                try:
                    rows = await brapi_fetch_history_legacy(ticker, date_from, date_to)
                    source = "brapi_legacy"
                except Exception as e:
                    logger.warning(f"[PriceHistory] BRAPI legado excecao para {ticker}: {e}")
        else:
            logger.info(
                f"[PriceHistory] {ticker} nao encontrado na BRAPI — pulando direto para yfinance"
            )

        # L3: yfinance (se BRAPI desconhece o ticker OU se BRAPI retornou vazio)
        if not rows:
            logger.info(f"[PriceHistory] tentando yfinance para {ticker}")
            try:
                rows = await _fetch_yf_history(ticker, asset_type, days_back)
                source = "yfinance_fallback"
            except Exception as e:
                logger.warning(f"[PriceHistory] yfinance excecao para {ticker}: {e}")

    # ── L4: Snapshot como ultimo recurso ─────────────────────────────────────
    if not rows:
        logger.info(f"[PriceHistory] sem historico para {ticker} — tentando snapshot")
        try:
            from app.integrations.brapi import fetch_quotes as brapi_fetch_quotes
            result = await brapi_fetch_quotes([ticker])
            price = result.get(ticker)
            if price:
                ts = _now_utc().replace(hour=_BR_CLOSE_HOUR_UTC, minute=0, second=0, microsecond=0)
                rows = [(ts, price)]
                source = "brapi_snapshot"
        except Exception as e:
            logger.warning(f"[PriceHistory] snapshot fallback falhou para {ticker}: {e}")

    inserted = 0
    for ts, close in rows:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        await _upsert_price(db, asset.id, ts, close, source)
        inserted += 1

    if inserted:
        latest_close = rows[-1][1] if rows else None
        if latest_close:
            asset.last_price = Decimal(str(round(latest_close, 8)))
            asset.last_price_updated_at = _now_utc()

    await db.commit()
    logger.info(f"[PriceHistory] {ticker}: {inserted} registros persistidos (source={source})")
    return inserted


async def get_price_at_date(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    target_date: str,
) -> Optional[float]:
    ref   = _parse_date_utc(target_date)
    since = ref - timedelta(days=5)
    until = ref + timedelta(hours=23, minutes=59, seconds=59)

    asset_result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    asset = asset_result.scalar_one_or_none()

    if asset:
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
        if price_row:
            return float(price_row.close)

    days_needed = (_now_utc().date() - ref.date()).days + 6
    await persist_daily_prices(db, ticker, asset_type, days_back=days_needed)

    asset_result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    asset = asset_result.scalar_one_or_none()
    if not asset:
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
    return float(price_row.close) if price_row else None


async def get_price_history(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    days: int = 90,
) -> list[dict]:
    asset_result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    asset = asset_result.scalar_one_or_none()

    if asset is None:
        await persist_daily_prices(db, ticker, asset_type, days_back=days)
        asset_result = await db.execute(select(Asset).where(Asset.ticker == ticker))
        asset = asset_result.scalar_one_or_none()
        if asset is None:
            return []
    else:
        last_ts = await _last_saved_ts(db, asset.id)
        if last_ts is None or (_now_utc() - last_ts).days > 1:
            await persist_daily_prices(db, ticker, asset_type, days_back=days)

    since = _now_utc() - timedelta(days=days)
    rows_result = await db.execute(
        select(AssetPrice)
        .where(AssetPrice.asset_id == asset.id, AssetPrice.timestamp >= since)
        .order_by(AssetPrice.timestamp.asc())
    )
    prices = rows_result.scalars().all()

    return [
        {"date": p.timestamp.strftime("%Y-%m-%d"), "close": float(p.close)}
        for p in prices
    ]
