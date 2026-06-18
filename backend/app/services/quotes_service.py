"""
Servico unificado de cotacoes.

Estrategia de cache em 3 camadas:
  L1 - Asset.last_price no banco (TTL = PRICE_TTL_SECONDS).
  L2 - Cache em memoria processo (TTL = MEM_CACHE_TTL).
  L3 - API externa: BRAPI Pro ou yfinance.
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

from app.core.asset_types import BR_TYPES, INTL_TYPES, NO_QUOTE_TYPES, yf_ticker
from app.integrations.brapi import (
    fetch_quotes as brapi_fetch_quotes,
    fetch_crypto_quote as brapi_fetch_crypto,
)
from app.models.asset import Asset, AssetType
from app.services.price_history_service import _YF_EXECUTOR  # pool global compartilhado

logger = logging.getLogger(__name__)

PRICE_TTL_SECONDS = 900
MEM_CACHE_TTL = 60

_mem_cache: dict[str, tuple[float, float]] = {}


def _mem_get(ticker: str) -> Optional[float]:
    entry = _mem_cache.get(ticker)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


def _mem_set(ticker: str, price: float) -> None:
    _mem_cache[ticker] = (price, time.time() + MEM_CACHE_TTL)


async def _db_get_fresh(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
) -> Optional[float]:
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
    result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    asset = result.scalar_one_or_none()
    if asset:
        asset.last_price = Decimal(str(round(price, 8)))
        asset.last_price_updated_at = datetime.now(timezone.utc)
        await db.flush()


def _fetch_yf_current_sync(ticker_map: dict[str, str]) -> dict[str, float]:
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
    ticker_map = {t: yf_ticker(t, at) for t, at in pairs}
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_YF_EXECUTOR, _fetch_yf_current_sync, ticker_map)


# ---------------------------------------------------------------------------
# Aliases mockaveis pelos testes
# ---------------------------------------------------------------------------

async def _fetch_brapi(tickers: list[str]) -> dict[str, float]:
    """Wrapper mockavel sobre brapi_fetch_quotes."""
    return await brapi_fetch_quotes(tickers)


async def _fetch_brapi_crypto(tickers: list[str]) -> dict[str, float]:
    """Wrapper mockavel sobre brapi_fetch_crypto."""
    return await brapi_fetch_crypto(tickers)


async def _fetch_yfinance(
    pairs: list[tuple[str, AssetType]],
) -> dict[str, float]:
    """Wrapper mockavel sobre _fetch_yfinance_current."""
    return await _fetch_yfinance_current(pairs)


async def _noop() -> dict:
    return {}


async def get_prices(
    positions: list[dict],
    db: Optional[AsyncSession] = None,
) -> dict[str, float]:
    br_tickers: list[str] = []
    crypto_tickers: list[str] = []
    intl_pairs: list[tuple[str, AssetType]] = []
    br_fallback: list[tuple[str, AssetType]] = []
    resolved: dict[str, float] = {}

    for p in positions:
        ticker = p["ticker"]
        raw_type = p.get("asset_type", "")
        try:
            asset_type = AssetType(raw_type) if isinstance(raw_type, str) else raw_type
        except ValueError:
            asset_type = None

        # Tipos sem cotacao de mercado (Tesouro, Renda Fixa, Outro) — pular silenciosamente
        if asset_type in NO_QUOTE_TYPES:
            logger.debug(f"[quotes_service] {ticker} ({raw_type}) sem cotacao de mercado — ignorado")
            continue

        mem_val = _mem_get(ticker)
        if mem_val is not None:
            resolved[ticker] = mem_val
            continue

        if db and asset_type:
            db_val = await _db_get_fresh(db, ticker, asset_type)
            if db_val is not None:
                resolved[ticker] = db_val
                _mem_set(ticker, db_val)
                continue

        if asset_type == AssetType.CRIPTO:
            crypto_tickers.append(ticker)
        elif asset_type in BR_TYPES:
            br_tickers.append(ticker)
        elif asset_type in INTL_TYPES:
            intl_pairs.append((ticker, asset_type))
        else:
            # Tipo desconhecido — tenta BRAPI como ultimo recurso e loga aviso
            logger.warning(f"[quotes_service] asset_type desconhecido para {ticker} ({raw_type}) — tentando BRAPI")
            br_tickers.append(ticker)

    br_results, crypto_results, intl_results = await asyncio.gather(
        _fetch_brapi(br_tickers) if br_tickers else _noop(),
        _fetch_brapi_crypto(crypto_tickers) if crypto_tickers else _noop(),
        _fetch_yfinance(intl_pairs) if intl_pairs else _noop(),
    )

    for p in positions:
        ticker = p["ticker"]
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
        logger.info(f"[quotes_service] BRAPI sem resposta para {[t for t, _ in br_fallback]} - tentando yfinance")
        fallback_results = await _fetch_yfinance(br_fallback)

    fresh = {**br_results, **crypto_results, **intl_results, **fallback_results}

    for p in positions:
        ticker = p["ticker"]
        raw_type = p.get("asset_type", "")
        price = fresh.get(ticker)
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


async def get_current_price(
    ticker: str,
    asset_type: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> Optional[float]:
    """
    Conveniencia: busca preco de um unico ticker.

    `asset_type` deve sempre ser passado para garantir o provedor correto.
    Se omitido, retorna None e loga aviso — evita silenciosamente usar ACAO como default.
    """
    if asset_type is None:
        logger.warning(f"[quotes_service] get_current_price chamado sem asset_type para {ticker} — retornando None")
        return None
    result = await get_prices([{"ticker": ticker, "asset_type": asset_type}], db)
    return result.get(ticker)


async def update_all_quotes(db: AsyncSession) -> int:
    """Atualiza last_price de todos os ativos cadastrados. Retorna quantidade atualizada."""
    result = await db.execute(select(Asset))
    assets = result.scalars().all()
    positions = [{"ticker": a.ticker, "asset_type": a.asset_type} for a in assets]
    prices = await get_prices(positions, db)
    await db.commit()
    return len(prices)
