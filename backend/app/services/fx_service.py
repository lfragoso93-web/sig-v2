"""
Servico de cotacoes cambiais com cache em 3 camadas.

Estrategia de cache:
  L2 - Memoria processo (MEM_CACHE_TTL = 60s)
  L1 - Tabela fx_rates no banco:
       * Datas historicas: permanentes (PTAX definitiva).
       * Data hoje: TTL de 900s (cotacao do dia ainda pode mudar).
  L3 - BCB PTAX (primario historico): fonte oficial, sem token, historico desde 1994.
       Fallback: AwesomeAPI se BCB falhar.
       Fallback final: FALLBACK_RATE.

Funcoes publicas:
  persist_usd_brl_rate(db, date_str, rate, commit=True) -> None
  get_usd_brl_today(db)                                -> float
  get_usd_brl_at_date(db, date_str)                    -> float
  get_usd_brl_batch(db, dates)                         -> dict

Datas futuras:
  Qualquer data >= hoje e tratada como hoje (retorna cotacao atual).
  Isso evita chamadas ao BCB com datas futuras que retornariam [] e
  aciona o FALLBACK_RATE desnecessariamente.

Fallback final: FALLBACK_RATE (5.70) — nunca levanta excecao.
"""
import logging
import time
from datetime import date as DateType, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.bcb import fetch_usd_brl_period, fetch_usd_brl_day
from app.models.fx_rate import FxRate

logger = logging.getLogger(__name__)

PAIR_USD_BRL = "USD-BRL"
FALLBACK_RATE = 5.70
MEM_CACHE_TTL = 60
DB_TODAY_TTL = 900
_RATE_QUANTUM = Decimal("0.00000001")

_mem_cache: dict[str, tuple[float, float]] = {}


def _normalize_rate(rate: float | Decimal) -> Decimal:
    return Decimal(str(rate)).quantize(_RATE_QUANTUM, rounding=ROUND_HALF_UP)


def _mem_get(date_str: str) -> Optional[float]:
    entry = _mem_cache.get(date_str)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


def _mem_set(date_str: str, rate: float, ttl: float = MEM_CACHE_TTL) -> None:
    _mem_cache[date_str] = (rate, time.time() + ttl)


async def _db_get(db: AsyncSession, date_str: str) -> Optional[float]:
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
        if d >= today and row.created_at:
            age = (datetime.now(timezone.utc) - row.created_at).total_seconds()
            if age > DB_TODAY_TTL:
                return None
        return float(row.rate)
    except Exception as e:
        logger.warning("[fx_service] _db_get error for %s: %s", date_str, e)
        return None


async def persist_usd_brl_rate(
    db: AsyncSession,
    date_str: str,
    rate: float | Decimal,
    *,
    commit: bool = True,
) -> None:
    """Persiste USD/BRL por UPSERT, com controle transacional pelo chamador.

    ``commit=True`` preserva o comportamento historico dos consumidores atuais.
    Orquestradores transacionais devem usar ``commit=False`` e controlar commit
    ou rollback externamente.
    """
    try:
        d = DateType.fromisoformat(date_str)
        now = datetime.now(timezone.utc)
        normalized_rate = _normalize_rate(rate)
        await db.execute(
            text("""
                INSERT INTO fx_rates (pair, rate_date, rate, created_at)
                VALUES (:pair, :rate_date, :rate, :created_at)
                ON CONFLICT (pair, rate_date)
                DO UPDATE SET rate = EXCLUDED.rate, created_at = EXCLUDED.created_at
            """),
            {
                "pair": PAIR_USD_BRL,
                "rate_date": d,
                "rate": normalized_rate,
                "created_at": now,
            },
        )
        if commit:
            await db.commit()
    except Exception:
        if commit:
            try:
                await db.rollback()
            except Exception:
                pass
        raise


async def _db_set(db: AsyncSession, date_str: str, rate: float) -> None:
    """Compatibilidade interna para consumidores existentes."""
    try:
        await persist_usd_brl_rate(db, date_str, rate, commit=True)
    except Exception as e:
        logger.warning("[fx_service] _db_set error for %s: %s", date_str, e)


async def _awesome_usd_brl_today() -> Optional[float]:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get("https://economia.awesomeapi.com.br/last/USD-BRL")
            resp.raise_for_status()
            data = resp.json()
            rate = data.get("USDBRL", {}).get("ask") or data.get("USDBRL", {}).get("bid")
            if rate:
                logger.info("[fx_service] AwesomeAPI USD/BRL hoje = %s", rate)
                return float(rate)
        return None
    except Exception as e:
        logger.warning("[fx_service] AwesomeAPI hoje falhou: %s", e)
        return None


async def _awesome_usd_brl_history(
    start_date: str,
    end_date: str,
) -> list[tuple[DateType, float]]:
    try:
        import httpx
        start_dt = DateType.fromisoformat(start_date)
        end_dt = DateType.fromisoformat(end_date)
        days = max((end_dt - start_dt).days + 10, 5)
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
        logger.info("[fx_service] AwesomeAPI historico USD/BRL: %d registros", len(rows))
        return rows
    except Exception as e:
        logger.warning("[fx_service] AwesomeAPI historico falhou: %s", e)
        return []


async def get_usd_brl_today(db: AsyncSession) -> float:
    today_str = datetime.now(timezone.utc).date().isoformat()
    cached = _mem_get(today_str)
    if cached is not None:
        return cached
    db_val = await _db_get(db, today_str)
    if db_val is not None:
        _mem_set(today_str, db_val)
        return db_val
    rate = await fetch_usd_brl_day(today_str)
    if rate is None:
        rate = await _awesome_usd_brl_today()
    if rate is None:
        logger.error(
            "[fx_service] todas as fontes falharam para USD/BRL hoje — usando FALLBACK_RATE=%s",
            FALLBACK_RATE,
        )
        rate = FALLBACK_RATE
    await _db_set(db, today_str, rate)
    _mem_set(today_str, rate)
    return rate


async def get_usd_brl_at_date(db: AsyncSession, date_str: str) -> float:
    today = datetime.now(timezone.utc).date()
    try:
        target = DateType.fromisoformat(date_str)
    except ValueError:
        logger.warning("[fx_service] date_str invalido: %r — usando hoje", date_str)
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
    rows = await fetch_usd_brl_period(window_start, date_str)
    if not rows:
        logger.info("[fx_service] BCB vazio para %s — tentando AwesomeAPI", date_str)
        rows = await _awesome_usd_brl_history(window_start, date_str)
    if rows:
        rate = rows[-1][1]
        for row_date, row_rate in rows:
            await _db_set(db, row_date.isoformat(), row_rate)
            _mem_set(row_date.isoformat(), row_rate, ttl=3600)
    else:
        logger.warning(
            "[fx_service] sem cotacao para %s — usando FALLBACK_RATE=%s",
            date_str, FALLBACK_RATE,
        )
        rate = FALLBACK_RATE
    return rate


async def get_usd_brl_batch(
    db: AsyncSession,
    dates: list[str],
) -> dict[str, float]:
    if not dates:
        return {}
    unique_dates = sorted(set(dates))
    result: dict[str, float] = {}
    missing: list[str] = []
    today = datetime.now(timezone.utc).date()
    for d_str in unique_dates:
        try:
            d = DateType.fromisoformat(d_str)
        except ValueError:
            continue
        if d >= today:
            rate_today = await get_usd_brl_today(db)
            result[d_str] = rate_today
            continue
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
    range_start = missing[0]
    range_end_dt = DateType.fromisoformat(missing[-1]) + timedelta(days=7)
    range_end = min(range_end_dt, today - timedelta(days=1)).isoformat()
    rows = await fetch_usd_brl_period(range_start, range_end)
    if not rows:
        logger.info("[fx_service] BCB vazio para range %s a %s — tentando AwesomeAPI", range_start, range_end)
        rows = await _awesome_usd_brl_history(range_start, range_end)
    fetched: dict[str, float] = {}
    for row_date, row_rate in rows:
        d_str = row_date.isoformat()
        fetched[d_str] = row_rate
        await _db_set(db, d_str, row_rate)
        _mem_set(d_str, row_rate, ttl=3600)
    for d_str in missing:
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
                logger.debug(
                    "[fx_service] %s sem PTAX (feriado?) — usando %s = %.4f",
                    d_str, closest, fetched[closest],
                )
            else:
                logger.warning(
                    "[fx_service] sem cotacao para %s — usando FALLBACK_RATE=%s",
                    d_str, FALLBACK_RATE,
                )
                result[d_str] = FALLBACK_RATE
    return result
