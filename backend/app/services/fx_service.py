"""
Servico de cotacoes cambiais com cache em 3 camadas.

Estrategia de cache:
  L2 - Memoria processo (MEM_CACHE_TTL = 60s) — evita roundtrips para
       cotacoes recentes buscadas na mesma requisicao/ciclo do scheduler.
  L1 - Tabela fx_rates no banco:
       * Datas HISTORICAS: permanentes (PTAX e definitiva — nunca muda).
       * Data HOJE: TTL de 900s (15min) — cotacao do dia ainda pode mudar.
  L3 - BRAPI /v2/currency (atual) e /v2/currency/historical (historico).
       Fallback: yfinance BRL=X se BRAPI falhar.
       Fallback final: AwesomeAPI (economia.awesomeapi.com.br).

Funcoes publicas:
  get_usd_brl_today(db)             -> float   cota hoje (L2 > L1 TTL > L3)
  get_usd_brl_at_date(db, date_str) -> float   cota historica (L2 > L1 perm > L3)
  get_usd_brl_batch(db, dates)      -> dict    multiplas datas em paralelo (otimizado)

Fallback final: se todas as fontes falharem, retorna FALLBACK_RATE (5.70)
com warning no log — nunca levanta excecao para nao quebrar portfolio_service.
"""
import asyncio
import logging
import time
from datetime import date as DateType, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.brapi import fetch_currency_rate, fetch_currency_history
from app.models.fx_rate import FxRate

logger = logging.getLogger(__name__)

PAIR_USD_BRL = "USD-BRL"
FALLBACK_RATE = 5.70
MEM_CACHE_TTL = 60
DB_TODAY_TTL = 900

# Cache L2: {date_str: (rate, expires_at)}
_mem_cache: dict[str, tuple[float, float]] = {}


# ---------------------------------------------------------------------------
# Helpers de cache L2
# ---------------------------------------------------------------------------

def _mem_get(date_str: str) -> Optional[float]:
    entry = _mem_cache.get(date_str)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


def _mem_set(date_str: str, rate: float, ttl: float = MEM_CACHE_TTL) -> None:
    _mem_cache[date_str] = (rate, time.time() + ttl)


# ---------------------------------------------------------------------------
# Helpers de banco (L1)
# ---------------------------------------------------------------------------

async def _db_get(db: AsyncSession, date_str: str) -> Optional[float]:
    """
    Busca cotacao em fx_rates.
    Para hoje: respeita TTL de 900s (cotacao ainda pode mudar).
    Para datas historicas: sempre valido (PTAX definitivo).
    """
    try:
        d = DateType.fromisoformat(date_str)
        result = await db.execute(
            select(FxRate).where(
                FxRate.pair == PAIR_USD_BRL,
                FxRate.rate_date == d,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        today = datetime.now(timezone.utc).date()
        if d >= today:
            if row.created_at:
                age = (datetime.now(timezone.utc) - row.created_at).total_seconds()
                if age > DB_TODAY_TTL:
                    return None
        return float(row.rate)
    except Exception as e:
        logger.warning(f"[fx_service] _db_get error for {date_str}: {e}")
        return None


async def _db_set(db: AsyncSession, date_str: str, rate: float) -> None:
    """
    Upsert atomico em fx_rates usando INSERT ... ON CONFLICT DO UPDATE.

    Resolve a race condition de requisicoes paralelas no startup:
    a primeira INSERT vence; as demais atualizam rate/created_at se a
    nova cotacao for mais recente. Nunca lanca excecao — erros sao logados.
    """
    try:
        d = DateType.fromisoformat(date_str)
        now = datetime.now(timezone.utc)
        rate_decimal = round(rate, 8)
        await db.execute(
            text("""
                INSERT INTO fx_rates (pair, rate_date, rate, created_at)
                VALUES (:pair, :rate_date, :rate, :created_at)
                ON CONFLICT (pair, rate_date)
                DO UPDATE SET
                    rate       = EXCLUDED.rate,
                    created_at = EXCLUDED.created_at
            """),
            {
                "pair":       PAIR_USD_BRL,
                "rate_date":  d,
                "rate":       rate_decimal,
                "created_at": now,
            },
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"[fx_service] _db_set error for {date_str}: {e}")
        try:
            await db.rollback()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Fallback yfinance para USD/BRL atual
# ---------------------------------------------------------------------------

async def _yf_usd_brl_today() -> Optional[float]:
    """Busca BRL=X via yfinance como fallback da BRAPI. Usa throttle global."""
    try:
        from app.services.price_history_service import _run_yf_with_throttle

        def _sync() -> Optional[float]:
            import yfinance as yf
            for ticker in ("BRL=X", "USDBRL=X"):
                try:
                    data = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
                    if not data.empty:
                        close = data["Close"].dropna()
                        if not close.empty:
                            return float(close.iloc[-1])
                except Exception:
                    continue
            return None

        return await _run_yf_with_throttle(_sync)
    except Exception as e:
        logger.warning(f"[fx_service] yfinance USD/BRL fallback falhou: {e}")
        return None


async def _yf_usd_brl_history(start_date: str, end_date: str) -> list[tuple[DateType, float]]:
    """Busca historico USD/BRL via yfinance como fallback da BRAPI. Usa throttle global."""
    try:
        from app.services.price_history_service import _run_yf_with_throttle

        def _sync() -> list[tuple[DateType, float]]:
            import yfinance as yf
            rows: list[tuple[DateType, float]] = []
            for ticker in ("BRL=X", "USDBRL=X"):
                try:
                    data = yf.download(
                        ticker,
                        start=start_date,
                        end=end_date,
                        interval="1d",
                        progress=False,
                        auto_adjust=True,
                    )
                    if not data.empty:
                        for idx, price in data["Close"].dropna().items():
                            d = idx.date() if hasattr(idx, "date") else DateType.fromisoformat(str(idx)[:10])
                            rows.append((d, float(price)))
                        if rows:
                            return rows
                except Exception:
                    continue
            return rows

        return await _run_yf_with_throttle(_sync)
    except Exception as e:
        logger.warning(f"[fx_service] yfinance historico USD/BRL fallback falhou: {e}")
        return []


# ---------------------------------------------------------------------------
# Fallback AwesomeAPI para USD/BRL (L3 extra)
# ---------------------------------------------------------------------------

async def _awesome_usd_brl_today() -> Optional[float]:
    """
    Busca cotacao USD/BRL via AwesomeAPI como terceira opcao de fallback.
    Endpoint publico, sem autenticacao necessaria.
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://economia.awesomeapi.com.br/last/USD-BRL")
            resp.raise_for_status()
            data = resp.json()
            rate = data.get("USDBRL", {}).get("ask") or data.get("USDBRL", {}).get("bid")
            if rate:
                logger.info(f"[fx_service] AwesomeAPI USD/BRL = {rate}")
                return float(rate)
        return None
    except Exception as e:
        logger.warning(f"[fx_service] AwesomeAPI fallback falhou: {e}")
        return None


async def _awesome_usd_brl_history(start_date: str, end_date: str) -> list[tuple[DateType, float]]:
    """
    Busca historico USD/BRL via AwesomeAPI.
    Endpoint: /json/daily/USD-BRL/{days}
    """
    try:
        import httpx
        from datetime import datetime
        start_dt = DateType.fromisoformat(start_date)
        end_dt = DateType.fromisoformat(end_date)
        days = (end_dt - start_dt).days + 10  # margem para fins de semana
        days = max(days, 5)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"https://economia.awesomeapi.com.br/json/daily/USD-BRL/{days}"
            )
            resp.raise_for_status()
            data = resp.json()
            rows: list[tuple[DateType, float]] = []
            for entry in data:
                ts = entry.get("timestamp")
                ask = entry.get("ask") or entry.get("bid")
                if ts and ask:
                    d = datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
                    if start_dt <= d <= end_dt:
                        rows.append((d, float(ask)))
            rows.sort(key=lambda x: x[0])
            logger.info(f"[fx_service] AwesomeAPI historico USD/BRL: {len(rows)} registros")
            return rows
    except Exception as e:
        logger.warning(f"[fx_service] AwesomeAPI historico fallback falhou: {e}")
        return []


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

async def get_usd_brl_today(db: AsyncSession) -> float:
    """
    Retorna a cotacao USD/BRL atual.

    Ordem: L2 mem -> L1 db (TTL 900s) -> L3 BRAPI -> L3 yfinance BRL=X -> L3 AwesomeAPI -> FALLBACK
    """
    today_str = datetime.now(timezone.utc).date().isoformat()

    cached = _mem_get(today_str)
    if cached is not None:
        return cached

    db_val = await _db_get(db, today_str)
    if db_val is not None:
        _mem_set(today_str, db_val)
        return db_val

    rate = await fetch_currency_rate(PAIR_USD_BRL)

    if rate is None:
        rate = await _yf_usd_brl_today()

    if rate is None:
        rate = await _awesome_usd_brl_today()

    if rate is None:
        logger.error(f"[fx_service] todas as fontes falharam para USD/BRL hoje — usando FALLBACK_RATE={FALLBACK_RATE}")
        rate = FALLBACK_RATE

    await _db_set(db, today_str, rate)
    _mem_set(today_str, rate)
    return rate


async def get_usd_brl_at_date(db: AsyncSession, date_str: str) -> float:
    """
    Retorna a cotacao USD/BRL em uma data especifica.

    Ordem: L2 mem -> L1 db (permanente) -> L3 BRAPI historico -> L3 yfinance -> L3 AwesomeAPI -> FALLBACK
    """
    today = datetime.now(timezone.utc).date()
    try:
        target = DateType.fromisoformat(date_str)
    except ValueError:
        logger.warning(f"[fx_service] date_str invalido: {date_str!r} — usando hoje")
        return await get_usd_brl_today(db)

    if target >= today:
        return await get_usd_brl_today(db)

    cached = _mem_get(date_str)
    if cached is not None:
        return cached

    db_val = await _db_get(db, date_str)
    if db_val is not None:
        _mem_set(date_str, db_val, ttl=3600)
        return db_val

    window_start = (target - timedelta(days=7)).isoformat()
    rows = await fetch_currency_history(PAIR_USD_BRL, window_start, date_str)

    if not rows:
        rows = await _yf_usd_brl_history(window_start, date_str)

    if not rows:
        rows = await _awesome_usd_brl_history(window_start, date_str)

    if rows:
        rate = rows[-1][1]
    else:
        logger.error(f"[fx_service] sem cotacao USD/BRL para {date_str} — usando FALLBACK_RATE={FALLBACK_RATE}")
        rate = FALLBACK_RATE

    for row_date, row_rate in rows:
        await _db_set(db, row_date.isoformat(), row_rate)
        _mem_set(row_date.isoformat(), row_rate, ttl=3600)

    return rate


async def get_usd_brl_batch(
    db: AsyncSession,
    dates: list[str],
) -> dict[str, float]:
    """
    Retorna {date_str: rate} para uma lista de datas.

    Otimizado: agrupa datas historicas ausentes em uma unica chamada BRAPI
    (range start..end) em vez de N chamadas individuais.
    """
    if not dates:
        return {}

    unique_dates = sorted(set(dates))
    result: dict[str, float] = {}
    missing: list[str] = []

    today = datetime.now(timezone.utc).date()

    for d_str in unique_dates:
        cached = _mem_get(d_str)
        if cached is not None:
            result[d_str] = cached
            continue
        db_val = await _db_get(db, d_str)
        if db_val is not None:
            result[d_str] = db_val
            _mem_set(d_str, db_val, ttl=3600)
            continue
        missing.append(d_str)

    if not missing:
        return result

    today_str = today.isoformat()
    needs_today = today_str in missing
    hist_missing = [d for d in missing if d != today_str]

    if needs_today:
        rate_today = await get_usd_brl_today(db)
        result[today_str] = rate_today

    if hist_missing:
        range_start = hist_missing[0]
        range_end_dt = DateType.fromisoformat(hist_missing[-1]) + timedelta(days=7)
        range_end = min(range_end_dt, today - timedelta(days=1)).isoformat()

        rows = await fetch_currency_history(PAIR_USD_BRL, range_start, range_end)
        if not rows:
            rows = await _yf_usd_brl_history(range_start, range_end)
        if not rows:
            rows = await _awesome_usd_brl_history(range_start, range_end)

        fetched: dict[str, float] = {}
        for row_date, row_rate in rows:
            d_str = row_date.isoformat()
            fetched[d_str] = row_rate
            await _db_set(db, d_str, row_rate)
            _mem_set(d_str, row_rate, ttl=3600)

        for d_str in hist_missing:
            if d_str in fetched:
                result[d_str] = fetched[d_str]
            else:
                target_dt = DateType.fromisoformat(d_str)
                closest = None
                for fd_str, fr in fetched.items():
                    fd = DateType.fromisoformat(fd_str)
                    if fd <= target_dt:
                        if closest is None or fd > DateType.fromisoformat(closest):
                            closest = fd_str
                if closest:
                    result[d_str] = fetched[closest]
                else:
                    logger.warning(f"[fx_service] sem cotacao para {d_str} — usando FALLBACK_RATE")
                    result[d_str] = FALLBACK_RATE

    return result
