"""
Servico unificado de cotações (Sprint 5).

Estratégia de cache em 3 camadas:
  L1 — Asset.last_price no banco (TTL = PRICE_TTL_SECONDS).
         Lido via `db` quando disponível; evita chamada externa completamente.
  L2 — Cache em memória processo (TTL = MEM_CACHE_TTL).
         Evita chamadas repetidas dentro da mesma janela de requests.
  L3 — API externa: BRAPI Pro (primário BR/cripto) ou yfinance (INTL + fallback BR).
         Após busca externa, persiste em L1 e L2.

Regras de provedor (definidas em app.core.asset_types):
  - BRAPI Pro → ACAO, FII, ETF_NACIONAL, TESOURO_DIRETO, RENDA_FIXA, CRIPTO
  - yfinance  → STOCK, ETF_INTERNACIONAL + fallback para qualquer BR sem resposta BRAPI
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import BR_TYPES, INTL_TYPES, yf_ticker
from app.integrations.brapi import (
    fetch_quotes      as brapi_fetch_quotes,
    fetch_crypto_quote as brapi_fetch_crypto,
)
from app.models.asset import Asset, AssetType

logger = logging.getLogger(__name__)

# ── TTLs ─────────────────────────────────────────────────────────────────────────
PRICE_TTL_SECONDS = 900   # 15 min — expiração do last_price no banco (L1)
MEM_CACHE_TTL     = 60    # 1 min  — cache em memória (L2); reduz hits ao banco

# ── Cache em memória (L2) ──────────────────────────────────────────────────────────
_mem_cache: dict[str, tuple[float, float]] = {}  # {ticker: (price, expires_at)}


def _mem_get(ticker: str) -> Optional[float]:
    entry = _mem_cache.get(ticker)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


def _mem_set(ticker: str, price: float) -> None:
    _mem_cache[ticker] = (price, time.time() + MEM_CACHE_TTL)


# ── Cache L1: last_price no banco ───────────────────────────────────────────────────

async def _db_get_fresh(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
) -> Optional[float]:
    """
    Lê Asset.last_price do banco.
    Retorna o valor somente se last_price_updated_at está dentro do TTL.
    """
    result = await db.execute(
        select(Asset.last_price, Asset.last_price_updated_at)
        .where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    row = result.first()
    if not row or row.last_price is None or row.last_price_updated_at is None:
        return None
    age = (datetime.now(timezone.utc) - row.last_price_updated_at).total_seconds()
    if age <= PRICE_TTL_SECONDS:
        return float(row.last_price)
    return None


async def _db_set(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    price: float,
) -> None:
    """
    Atualiza Asset.last_price e last_price_updated_at no banco.
    Opera com UPDATE direto — não cria o ativo se não existir.
    """
    result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    asset = result.scalar_one_or_none()
    if asset:
        asset.last_price            = Decimal(str(round(price, 8)))
        asset.last_price_updated_at = datetime.now(timezone.utc)
        # flush sem commit — o commit fica a cargo do caller (portfolio_service)
        await db.flush()


# ── yfinance (cotacao atual, sync no executor do price_history_service) ──────────

from app.services.price_history_service import _YF_EXECUTOR  # pool global compartilhado


def _fetch_yf_current_sync(ticker_map: dict[str, str]) -> dict[str, float]:
    """
    Busca cotação atual via yf.download (period=1d, interval=1m).
    ticker_map: {ticker_interno: ticker_yfinance}
    """
    if not ticker_map:
        return {}
    yf_syms = list(ticker_map.values())
    results: dict[str, float] = {}
    try:
        data = yf.download(
            tickers=yf_syms,
            period="1d",
            interval="1m",
            progress=False,
            auto_adjust=True,
        )
        if data.empty:
            return {}
        close = data["Close"] if "Close" in data.columns else data
        for internal, sym in ticker_map.items():
            try:
                price = float(
                    close.iloc[-1] if len(yf_syms) == 1
                    else close[sym].dropna().iloc[-1]
                )
                results[internal] = price
            except Exception as e:
                logger.warning(f"yfinance preco nao encontrado para {sym}: {e}")
    except Exception as e:
        logger.error(f"yfinance download error: {e}")
    return results


async def _fetch_yfinance_current(
    pairs: list[tuple[str, AssetType]],
) -> dict[str, float]:
    """Wrapper async para _fetch_yf_current_sync usando o executor global."""
    ticker_map = {t: yf_ticker(t, at) for t, at in pairs}
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_YF_EXECUTOR, _fetch_yf_current_sync, ticker_map)


async def _noop() -> dict:
    return {}


# ── API pública ─────────────────────────────────────────────────────────────────────────

async def get_prices(
    positions: list[dict],
    db: Optional[AsyncSession] = None,
) -> dict[str, float]:
    """
    Retorna {ticker: current_price} para a lista de posições.

    Cada item de `positions` deve ter 'ticker' e 'asset_type' (valor do enum AssetType).
    Tickers ausentes no resultado = cotação indisponível.
    Nunca retorna PM como fallback de cotação.

    Camadas consultadas na ordem:
      1. Cache em memória (L2, 1 min)
      2. Asset.last_price no banco (L1, 15 min) — se `db` fornecido
      3. BRAPI Pro (BR/cripto) ou yfinance (INTL)
         3a. yfinance como fallback se BRAPI retornar sem o ticker
    """
    br_tickers:    list[str]                   = []
    crypto_tickers: list[str]                  = []
    intl_pairs:    list[tuple[str, AssetType]] = []
    br_fallback:   list[tuple[str, AssetType]] = []  # BR sem resposta BRAPI
    resolved:      dict[str, float]            = {}  # tickers já resolvidos (L1/L2)

    # ─ Classifica por provedor e verifica caches ─────────────────────────────────
    for p in positions:
        ticker     = p["ticker"]
        raw_type   = p.get("asset_type", "")

        # Normaliza: aceita string ou enum
        try:
            asset_type = AssetType(raw_type) if isinstance(raw_type, str) else raw_type
        except ValueError:
            asset_type = None

        # L2: cache em memória
        mem_val = _mem_get(ticker)
        if mem_val is not None:
            resolved[ticker] = mem_val
            continue

        # L1: last_price no banco
        if db and asset_type:
            db_val = await _db_get_fresh(db, ticker, asset_type)
            if db_val is not None:
                resolved[ticker] = db_val
                _mem_set(ticker, db_val)  # popula L2
                continue

        # Classifica para busca externa (L3)
        if asset_type == AssetType.CRIPTO:
            crypto_tickers.append(ticker)
        elif asset_type in BR_TYPES:
            br_tickers.append(ticker)
        elif asset_type in INTL_TYPES:
            intl_pairs.append((ticker, asset_type))
        else:
            br_tickers.append(ticker)  # tipo desconhecido: tenta BRAPI

    # ─ L3: chamadas externas em paralelo ────────────────────────────────────────────
    br_results, crypto_results, intl_results = await asyncio.gather(
        brapi_fetch_quotes(br_tickers)          if br_tickers     else _noop(),
        brapi_fetch_crypto(crypto_tickers)      if crypto_tickers else _noop(),
        _fetch_yfinance_current(intl_pairs)     if intl_pairs     else _noop(),
    )

    # ─ Fallback yfinance para ativos BR sem resposta BRAPI ──────────────────────
    for p in positions:
        ticker   = p["ticker"]
        raw_type = p.get("asset_type", "")
        try:
            asset_type = AssetType(raw_type) if isinstance(raw_type, str) else raw_type
        except ValueError:
            asset_type = None

        if (
            ticker in br_tickers
            and ticker not in br_results
            and ticker not in resolved
            and asset_type is not None
        ):
            br_fallback.append((ticker, asset_type))

    fallback_results: dict[str, float] = {}
    if br_fallback:
        logger.info(f"[quotes_service] BRAPI sem resposta para {[t for t,_ in br_fallback]} — tentando yfinance")
        fallback_results = await _fetch_yfinance_current(br_fallback)

    # ─ Consolida todos os resultados ────────────────────────────────────────────────
    fresh = {**br_results, **crypto_results, **intl_results, **fallback_results}

    # Persiste em L1 (banco) e L2 (memória) os preços recém-buscados
    for p in positions:
        ticker   = p["ticker"]
        raw_type = p.get("asset_type", "")
        price    = fresh.get(ticker)
        if price is None:
            continue
        _mem_set(ticker, price)
        if db:
            try:
                asset_type = AssetType(raw_type) if isinstance(raw_type, str) else raw_type
                await _db_set(db, ticker, asset_type, price)
            except Exception as e:
                logger.warning(f"[quotes_service] falha ao persistir last_price para {ticker}: {e}")

    return {**resolved, **fresh}
