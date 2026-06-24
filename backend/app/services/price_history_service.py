"""
Servico de historico de precos.

Estrategia de busca (por camadas):

  Ativos BR (ACAO, FII, ETF_NACIONAL, BDR, CRIPTO):
    L0 - Validacao BRAPI: verifica se o ticker e conhecido pela BRAPI via
         cache em memoria (populado pelo seed via /api/v2/tickers).
         Tickers desconhecidos pulam direto para yfinance.
    L1 - BRAPI v2:
         FII -> /api/v2/fii/historical
         demais -> /api/v2/stocks/historical
         Se v2 retornar vazio para ticker CONHECIDO, vai direto para
         yfinance (sem tentar legado que retornaria 400).
    L2 - BRAPI legado /quote/{ticker} com startDate/endDate
         Usado apenas como fallback extra dentro de fetch_price_history.
    L3 - yfinance (fallback final)
    L4 - Snapshot BRAPI (ultimo recurso)

  Ativos INTL (STOCK, ETF_INTERNACIONAL):
    L1 - Alpha Vantage TIME_SERIES_DAILY (primario)
    L2 - yfinance (fallback)
    L3 - Snapshot BRAPI (ultimo recurso)

Ancoragem por transacao (_earliest_transaction_date):
  Quando o caller nao especifica days_back suficiente para cobrir
  todo o periodo de posse, persist_daily_prices expande a janela
  automaticamente ate a data da transacao mais antiga do ticker.
  Isso garante historico completo para calculo de rentabilidade e IRPF.

Cooldown de persistencia (_persist_cooldown):
  Apos persistir com sucesso, o ticker fica em cooldown por
  PERSIST_COOLDOWN_SECONDS (1800s = 30min). Chamadas dentro do cooldown
  retornam 0 imediatamente sem acionar BRAPI ou yfinance.
  Isso evita YFRateLimitError quando multiplos endpoints (summary,
  positions, asset-distribution) chegam em paralelo para os mesmos tickers.

  force=True bypassa o cooldown e o limite de days_back por last_ts.
  Usado pelo _prefetch_price_history no backfill para garantir que o
  historico completo seja buscado mesmo que o ticker ja tenha dados recentes.

Rate limiting yfinance (threading.Lock - nivel de thread):
  _yf_thread_lock garante que apenas uma thread execute yfinance de cada vez.
  _YF_MIN_INTERVAL (12s) adiciona pausa minima para evitar 429.

Lock por ticker (_ticker_locks):
  Evita requests duplicados concorrentes para o mesmo ticker.

Rate limiting Alpha Vantage:
  alpha_vantage_limiter (TokenBucket, 4 req/min) em core/rate_limiter.py.
"""
import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
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
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# -- yfinance thread pool e rate limiter --------------------------------------
_YF_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="yfinance_hist")
_yf_thread_lock = threading.Lock()
_YF_MIN_INTERVAL: float = 12.0
_yf_last_call: list[float] = [0.0]

# -- Cooldown de persistencia -------------------------------------------------
# Evita chamadas repetidas a BRAPI/yfinance quando multiplos endpoints
# chegam em paralelo para os mesmos tickers (summary, positions, etc.).
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
    """Remove o ticker do cooldown. Usado pelo prefetch forcado do backfill."""
    with _cooldown_lock:
        _persist_cooldown.pop(ticker, None)


# -- Lock por ticker ----------------------------------------------------------
_ticker_locks: dict[str, asyncio.Lock] = {}
_ticker_locks_mutex = threading.Lock()


def _get_ticker_lock(ticker: str) -> asyncio.Lock:
    with _ticker_locks_mutex:
        if ticker not in _ticker_locks:
            _ticker_locks[ticker] = asyncio.Lock()
        return _ticker_locks[ticker]


# -- Tipos BRAPI v2 -----------------------------------------------------------
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


async def _first_saved_ts(db: AsyncSession, asset_id: int) -> Optional[datetime]:
    """Retorna o timestamp mais antigo salvo para o asset."""
    result = await db.execute(
        select(func.min(AssetPrice.timestamp)).where(AssetPrice.asset_id == asset_id)
    )
    return result.scalar_one_or_none()


async def _earliest_transaction_date(db: AsyncSession, ticker: str) -> Optional[date]:
    """
    Retorna a data da transacao mais antiga registrada para o ticker
    em qualquer carteira do sistema.

    Essa data e usada como ancora do historico: garante que os precos
    cubram todo o periodo de posse do ativo, necessario para calculo
    correto de preco medio, rentabilidade e IRPF.
    """
    result = await db.execute(
        select(func.min(Transaction.date)).where(
            Transaction.ticker == ticker.upper()
        )
    )
    return result.scalar_one_or_none()


def _fetch_yf_history_sync(yf_sym: str, days: int) -> list[tuple[datetime, float]]:
    """
    Busca historico via yfinance usando start/end explicitos.

    Nao usa period='{days}d' pois yfinance so aceita periodos fixos
    (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max). Valores
    como '365d' ou '730d' retornam DataFrame vazio silenciosamente.
    """
    try:
        from datetime import date as _date
        tk = yf.Ticker(yf_sym)
        start_date = _date.today() - timedelta(days=days)
        # end e exclusivo no yfinance: +1 dia para incluir hoje
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
    force: bool = False,
) -> int:
    """
    Persiste historico de precos diarios para um ativo.

    A janela de busca e expandida automaticamente ate a data da transacao
    mais antiga do ticker (se existir e for anterior a days_back calculado),
    garantindo cobertura completa do periodo de posse para IRPF e rentabilidade.

    force=True: ignora cooldown e o limite de days_back por last_ts.
    Usar apenas no _prefetch_price_history do backfill.

    Retorna 0 imediatamente se o ticker estiver em cooldown E force=False.
    """
    if asset_type in NO_QUOTE_TYPES:
        logger.debug(f"[PriceHistory] {ticker} ({asset_type}) sem cotacao — ignorado")
        return 0

    if not force and _is_in_cooldown(ticker):
        logger.debug(f"[PriceHistory] {ticker} em cooldown — pulando")
        return 0

    if force:
        _clear_cooldown(ticker)

    lock = _get_ticker_lock(ticker)
    async with lock:
        if not force and _is_in_cooldown(ticker):
            logger.debug(f"[PriceHistory] {ticker} em cooldown (pos-lock) — pulando")
            return 0
        return await _persist_daily_prices_inner(db, ticker, asset_type, days_back, force=force)


async def _persist_daily_prices_inner(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    days_back: int,
    force: bool = False,
) -> int:
    asset = await _get_or_create_asset(db, ticker, asset_type)
    last_ts = await _last_saved_ts(db, asset.id)

    if not force and last_ts:
        delta = (_now_utc() - last_ts).days
        if delta < 1:
            logger.debug(f"[PriceHistory] {ticker} banco atualizado (last={last_ts.date()}) — pulando")
            _set_cooldown(ticker)
            return 0
        days_back = min(days_back, max(delta + 1, 2))
    elif force and last_ts:
        # Com force=True: calcula a janela real desde o inicio dos dados salvos
        # vs o days_back solicitado, e usa o maior (garante sem gaps).
        first_ts = await _first_saved_ts(db, asset.id)
        if first_ts:
            days_already = (_now_utc() - first_ts).days
            if days_already >= days_back:
                delta = (_now_utc() - last_ts).days
                if delta < 1:
                    logger.debug(
                        f"[PriceHistory] {ticker} historico completo (first={first_ts.date()}, "
                        f"last={last_ts.date()}) — pulando prefetch"
                    )
                    _set_cooldown(ticker)
                    return 0
                days_back = max(delta + 1, 2)
                logger.info(
                    f"[PriceHistory] {ticker} force=True mas historico ja cobre {days_already}d "
                    f"(pedido={days_back}d) — atualizando apenas delta={delta}d"
                )
            else:
                logger.info(
                    f"[PriceHistory] {ticker} force=True: historico existente cobre {days_already}d, "
                    f"pedido={days_back}d — buscando completo"
                )

    # -- Ancora na transacao mais antiga do ticker ----------------------------
    # Garante que o historico cubra desde a primeira compra/venda registrada,
    # independente do days_back passado pelo caller.
    earliest_tx = await _earliest_transaction_date(db, ticker)
    if earliest_tx:
        days_since_first_tx = (_now_utc().date() - earliest_tx).days
        if days_since_first_tx > days_back:
            logger.info(
                f"[PriceHistory] {ticker} expandindo janela: days_back={days_back} "
                f"< dias desde primeira transacao={days_since_first_tx} "
                f"(first_tx={earliest_tx}) — usando {days_since_first_tx}d"
            )
            days_back = days_since_first_tx

    date_to   = _now_utc().date().isoformat()
    date_from = (_now_utc().date() - timedelta(days=days_back)).isoformat()

    rows:   list[tuple[datetime, float]] = []
    source: str = ""
    is_intl = asset_type in INTL_TYPES

    if is_intl:
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
        brapi_known = await is_known_by_brapi(ticker)

        if brapi_known:
            rows, source = await _fetch_brapi_v2(ticker, asset_type, date_from, date_to)

            if not rows:
                logger.info(
                    f"[PriceHistory] BRAPI v2 vazio para {ticker} ({asset_type}) "
                    f"— pulando legado, tentando yfinance"
                )
        else:
            logger.info(
                f"[PriceHistory] {ticker} nao encontrado na BRAPI — pulando direto para yfinance"
            )

        if not rows:
            try:
                rows = await _fetch_yf_history(ticker, asset_type, days_back)
                source = "yfinance_fallback"
            except Exception as e:
                logger.warning(f"[PriceHistory] yfinance excecao para {ticker}: {e}")

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
    logger.info(f"[PriceHistory] {ticker}: {inserted} registros persistidos (source={source}, force={force})")

    _set_cooldown(ticker)
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
