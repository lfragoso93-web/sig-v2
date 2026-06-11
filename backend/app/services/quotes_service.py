"""
Servico unificado de cotacoes.
Busca precos reais via BRAPI (ativos BR + cripto) e yfinance (internacionais).
Usa cache em memoria por 5 minutos para nao sobrecarregar as APIs.
"""
import asyncio
import logging
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

from app.integrations.brapi import fetch_quotes as brapi_fetch_quotes

logger = logging.getLogger(__name__)

# ── Tipos por origem ────────────────────────────────────────────────────────────
# Ativos nacionais + cripto → BRAPI (retorna BRL)
BR_TYPES = {
    'ACAO', 'ACAO_NACIONAL', 'FII',
    'ETF_NACIONAL', 'TESOURO_DIRETO', 'RENDA_FIXA',
    'CRIPTO', 'CRIPTOMOEDA',  # BRAPI tem endpoint cripto em BRL
}
# Internacionais → yfinance
INTL_TYPES = {'STOCK', 'ETF_INTERNACIONAL'}

# ── Cache simples em memoria ─────────────────────────────────────────────────────
CACHE_TTL = 300  # 5 minutos
_cache: dict[str, tuple[float, float]] = {}  # {ticker: (price, expires_at)}


def _cache_get(ticker: str) -> Optional[float]:
    entry = _cache.get(ticker)
    if entry and time.time() < entry[1]:
        return entry[0]
    return None


def _cache_set(ticker: str, price: float) -> None:
    _cache[ticker] = (price, time.time() + CACHE_TTL)


# ── yfinance (sync em thread) ────────────────────────────────────────────────────

def _to_yf_symbol(ticker: str, asset_type: str) -> str:
    """Converte ticker interno para simbolo yfinance (apenas INTL)."""
    return ticker.upper()


def _fetch_yf_sync(ticker_map: dict[str, str]) -> dict[str, float]:
    """Executa yf.download em thread separada."""
    if not ticker_map:
        return {}
    yf_symbols = list(ticker_map.values())
    results: dict[str, float] = {}
    try:
        data = yf.download(
            tickers=yf_symbols,
            period='1d',
            interval='1m',
            progress=False,
            auto_adjust=True,
        )
        if data.empty:
            return {}
        close = data['Close'] if 'Close' in data.columns else data
        for internal, sym in ticker_map.items():
            try:
                price = float(
                    close.iloc[-1] if len(yf_symbols) == 1
                    else close[sym].dropna().iloc[-1]
                )
                results[internal] = price
            except Exception as e:
                logger.warning(f'yfinance preco nao encontrado para {sym}: {e}')
    except Exception as e:
        logger.error(f'yfinance download error: {e}')
    return results


async def _fetch_yfinance(ticker_asset_pairs: list[tuple[str, str]]) -> dict[str, float]:
    """Busca cotacoes internacionais via yfinance (async wrapper)."""
    ticker_map = {
        ticker: _to_yf_symbol(ticker, asset_type)
        for ticker, asset_type in ticker_asset_pairs
    }
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(pool, _fetch_yf_sync, ticker_map)


async def _noop() -> dict:
    return {}


# ── BRAPI cripto ─────────────────────────────────────────────────────────────────
async def _fetch_brapi_crypto(pairs: list[tuple[str, str]]) -> dict[str, float]:
    """Busca cotacao de cripto via BRAPI /api/v2/crypto?coin=BTC&currency=BRL."""
    from app.integrations.brapi import _auth_headers
    import httpx
    results: dict[str, float] = {}
    headers = _auth_headers()
    async with httpx.AsyncClient(timeout=10.0) as client:
        for ticker, _ in pairs:
            try:
                resp = await client.get(
                    'https://brapi.dev/api/v2/crypto',
                    headers=headers,
                    params={'coin': ticker, 'currency': 'BRL'},
                )
                resp.raise_for_status()
                data  = resp.json()
                coins = data.get('coins') or []
                if coins:
                    price = coins[0].get('regularMarketPrice') or coins[0].get('price')
                    if price:
                        results[ticker] = float(price)
            except Exception as e:
                logger.warning(f'BRAPI cripto price error for {ticker}: {e}')
    return results


# ── API publica ────────────────────────────────────────────────────────────────────

async def get_prices(positions: list[dict]) -> dict[str, float]:
    """
    Recebe lista de dicts com 'ticker' e 'asset_type'.
    Retorna {ticker: current_price}.
    Retorna dict parcial (ticker ausente = cotacao indisponivel, NAO usar avg como fallback).
    Usa cache em memoria (5 min).
    """
    br_tickers:    list[str]              = []
    crypto_pairs:  list[tuple[str, str]]  = []
    intl_pairs:    list[tuple[str, str]]  = []
    cached:        dict[str, float]       = {}

    for p in positions:
        ticker     = p['ticker']
        asset_type = p.get('asset_type', '').upper()
        cached_val = _cache_get(ticker)
        if cached_val is not None:
            cached[ticker] = cached_val
            continue

        if asset_type in ('CRIPTO', 'CRIPTOMOEDA'):
            crypto_pairs.append((ticker, asset_type))
        elif asset_type in BR_TYPES:
            br_tickers.append(ticker)
        elif asset_type in INTL_TYPES:
            intl_pairs.append((ticker, asset_type))
        else:
            # tipo desconhecido: tenta BRAPI como fallback
            br_tickers.append(ticker)

    br_results, crypto_results, intl_results = await asyncio.gather(
        brapi_fetch_quotes(br_tickers) if br_tickers   else _noop(),
        _fetch_brapi_crypto(crypto_pairs) if crypto_pairs else _noop(),
        _fetch_yfinance(intl_pairs)    if intl_pairs   else _noop(),
    )

    all_prices = {**cached, **br_results, **crypto_results, **intl_results}

    for ticker, price in {**br_results, **crypto_results, **intl_results}.items():
        _cache_set(ticker, price)

    return all_prices
