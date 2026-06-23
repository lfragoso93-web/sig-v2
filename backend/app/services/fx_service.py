"""
Servico de cotacoes cambiais com cache em 3 camadas.

Estrategia de cache:
  L2 - Memoria processo (MEM_CACHE_TTL = 60s) — evita roundtrips para
       cotacoes recentes buscadas na mesma requisicao/ciclo do scheduler.
  L1 - Tabela fx_rates no banco:
       * Datas HISTORICAS: permanentes (PTAX e definitiva — nunca muda).
       * Data HOJE: TTL de 900s (15min) — cotacao do dia ainda pode mudar.
  L3 - BRAPI /v2/currency (atual) e /v2/currency/historical (historico).
       Fallback: yfinance USDBRL=X se BRAPI falhar.

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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.brapi import fetch_currency_rate, fetch_currency_history
from app.models.fx_rate import FxRate

logger = logging.getLogger(__name__)

PAIR_USD_BRL = "USD-BRL"
FALLBACK_RATE = 5.70          # usado apenas se todas as fontes falharem
MEM_CACHE_TTL = 60            # segundos — L2 para cotacao do dia
DB_TODAY_TTL = 900            # segundos — L1 TTL para cotacao de hoje

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
            # cotacao de hoje: verificar TTL
            if row.created_at:
                age = (datetime.now(timezone.utc) - row.created_at).total_seconds()
                if age > DB_TODAY_TTL:
                    return None  # expirado — buscar novamente
        # historico ou hoje dentro do TTL
        return float(row.rate)
    except Exception as e:
        logger.warning(f"[fx_service] _db_get error for {date_str}: {e}")
        return None


async def _db_set(db: AsyncSession, date_str: str, rate: float) -> None:
    """
    Upsert em fx_rates via savepoint — commit independente da transacao principal.
    Idempotente: se ja existe, atualiza apenas rate e created_at.
    """
    try:
        d = DateType.fromisoformat(date_str)
        async with db.begin_nested():
            result = await db.execute(
                select(FxRate).where(
                    FxRate.pair == PAIR_USD_BRL,
                    FxRate.rate_date == d,
                )
            )
            row = result.scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if row:
                row.rate = Decimal(str(round(rate, 8)))
                row.created_at = now
            else:
                db.add(FxRate(
                    pair=PAIR_USD_BRL,
                    rate_date=d,
                    rate=Decimal(str(round(rate, 8))),
                    created_at=now,
                ))
    except Exception as e:
        logger.warning(f"[fx_service] _db_set error for {date_str}: {e}")


# ---------------------------------------------------------------------------
# Fallback yfinance para USD/BRL atual
# ---------------------------------------------------------------------------

async def _yf_usd_brl_today() -> Optional[float]:
    """Busca USDBRL=X via yfinance como fallback da BRAPI."""
    try:
        import asyncio
        import yfinance as yf
        from app.services.price_history_service import _YF_EXECUTOR

        def _sync() -> Optional[float]:
            import yfinance as yf
            data = yf.download("USDBRL=X", period="1d", interval="1m", progress=False, auto_adjust=True)
            if data.empty:
                return None
            return float(data["Close"].dropna().iloc[-1])

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_YF_EXECUTOR, _sync)
    except Exception as e:
        logger.warning(f"[fx_service] yfinance USDBRL=X fallback falhou: {e}")
        return None


async def _yf_usd_brl_history(start_date: str, end_date: str) -> list[tuple[DateType, float]]:
    """Busca historico USD/BRL via yfinance como fallback da BRAPI."""
    try:
        import yfinance as yf
        from app.services.price_history_service import _YF_EXECUTOR

        def _sync() -> list[tuple[DateType, float]]:
            data = yf.download(
                "USDBRL=X",
                start=start_date,
                end=end_date,
                interval="1d",
                progress=False,
                auto_adjust=True,
            )
            if data.empty:
                return []
            rows = []
            for idx, price in data["Close"].dropna().items():
                d = idx.date() if hasattr(idx, "date") else DateType.fromisoformat(str(idx)[:10])
                rows.append((d, float(price)))
            return rows

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_YF_EXECUTOR, _sync)
    except Exception as e:
        logger.warning(f"[fx_service] yfinance historico USD/BRL fallback falhou: {e}")
        return []


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

async def get_usd_brl_today(db: AsyncSession) -> float:
    """
    Retorna a cotacao USD/BRL atual.

    Ordem: L2 mem -> L1 db (TTL 900s) -> L3 BRAPI -> L3 yfinance -> FALLBACK_RATE
    """
    today_str = datetime.now(timezone.utc).date().isoformat()

    # L2
    cached = _mem_get(today_str)
    if cached is not None:
        return cached

    # L1
    db_val = await _db_get(db, today_str)
    if db_val is not None:
        _mem_set(today_str, db_val)
        return db_val

    # L3 BRAPI
    rate = await fetch_currency_rate(PAIR_USD_BRL)

    # L3 yfinance fallback
    if rate is None:
        rate = await _yf_usd_brl_today()

    if rate is None:
        logger.error(f"[fx_service] todas as fontes falharam para USD/BRL hoje — usando FALLBACK_RATE={FALLBACK_RATE}")
        rate = FALLBACK_RATE

    await _db_set(db, today_str, rate)
    _mem_set(today_str, rate)
    return rate


async def get_usd_brl_at_date(db: AsyncSession, date_str: str) -> float:
    """
    Retorna a cotacao USD/BRL em uma data especifica.

    Para datas historicas, o valor e permanente no banco (PTAX definitivo).
    Para hoje, delega para get_usd_brl_today().

    Ordem: L2 mem -> L1 db (permanente) -> L3 BRAPI historico -> L3 yfinance -> FALLBACK_RATE
    """
    today = datetime.now(timezone.utc).date()
    try:
        target = DateType.fromisoformat(date_str)
    except ValueError:
        logger.warning(f"[fx_service] date_str invalido: {date_str!r} — usando hoje")
        return await get_usd_brl_today(db)

    if target >= today:
        return await get_usd_brl_today(db)

    # L2
    cached = _mem_get(date_str)
    if cached is not None:
        return cached

    # L1 (permanente para historico)
    db_val = await _db_get(db, date_str)
    if db_val is not None:
        _mem_set(date_str, db_val, ttl=3600)  # 1h em mem para historico
        return db_val

    # L3 BRAPI historico — janela de 7 dias antes para cobrir feriados
    window_start = (target - timedelta(days=7)).isoformat()
    rows = await fetch_currency_history(PAIR_USD_BRL, window_start, date_str)

    if not rows:
        # Fallback yfinance
        rows = await _yf_usd_brl_history(window_start, date_str)

    if rows:
        # Usa o ultimo valor disponivel na janela (mais proximo da data alvo)
        rate = rows[-1][1]
    else:
        logger.error(f"[fx_service] sem cotacao USD/BRL para {date_str} — usando FALLBACK_RATE={FALLBACK_RATE}")
        rate = FALLBACK_RATE

    # Persiste cada data retornada no banco (evita reprocessar o mesmo range)
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

    Otimizado para portfolio_service: agrupa datas historicas ausentes no banco
    em uma unica chamada BRAPI (range start..end) em vez de N chamadas individuais.

    Datas duplicadas sao deduplicadas automaticamente.
    """
    if not dates:
        return {}

    unique_dates = sorted(set(dates))
    result: dict[str, float] = {}
    missing: list[str] = []

    today = datetime.now(timezone.utc).date()

    for d_str in unique_dates:
        # L2
        cached = _mem_get(d_str)
        if cached is not None:
            result[d_str] = cached
            continue
        # L1
        db_val = await _db_get(db, d_str)
        if db_val is not None:
            result[d_str] = db_val
            _mem_set(d_str, db_val, ttl=3600)
            continue
        missing.append(d_str)

    if not missing:
        return result

    # Separa hoje das datas historicas
    today_str = today.isoformat()
    needs_today = today_str in missing
    hist_missing = [d for d in missing if d != today_str]

    # Cotacao de hoje
    if needs_today:
        rate_today = await get_usd_brl_today(db)
        result[today_str] = rate_today

    # Historico em bloco: um unico range cobrindo todas as datas ausentes
    if hist_missing:
        range_start = hist_missing[0]
        # Adiciona 7 dias alem do fim para cobrir fins de semana/feriados
        range_end_dt = DateType.fromisoformat(hist_missing[-1]) + timedelta(days=7)
        range_end = min(range_end_dt, today - timedelta(days=1)).isoformat()

        rows = await fetch_currency_history(PAIR_USD_BRL, range_start, range_end)
        if not rows:
            rows = await _yf_usd_brl_history(range_start, range_end)

        # Mapeia por date_str para lookup rapido
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
                # Busca o dia disponivel mais proximo antes da data alvo
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
