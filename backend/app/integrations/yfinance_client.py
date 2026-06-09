import logging
from typing import Optional
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import asyncio

logger = logging.getLogger(__name__)

# Tipos que usam yfinance
INTERNATIONAL_TYPES = {
    "stock",
    "etf internacional",
    "criptomoeda",
}

# Sufixos de cripto para yfinance (ex: BTC -> BTC-USD)
CRYPTO_SUFFIX = "-USD"


def _ticker_to_yf(ticker: str, asset_type: str) -> str:
    """Converte ticker interno para formato yfinance."""
    t = asset_type.lower()
    if t == "criptomoeda":
        # BTC -> BTC-USD, ETH -> ETH-USD
        return ticker.upper() + CRYPTO_SUFFIX
    # Stocks e ETFs internacionais ja vem no formato correto (ex: AAPL, VTI)
    return ticker.upper()


def _fetch_prices_sync(ticker_map: dict[str, str]) -> dict[str, float]:
    """
    ticker_map: {ticker_interno: ticker_yf}
    Retorna {ticker_interno: preco}.
    Executado em thread para nao bloquear o event loop.
    """
    if not ticker_map:
        return {}

    yf_tickers = list(ticker_map.values())
    results: dict[str, float] = {}

    try:
        data = yf.download(
            tickers=yf_tickers,
            period="1d",
            interval="1m",
            progress=False,
            auto_adjust=True,
        )

        if data.empty:
            return {}

        # Pega o ultimo preco disponivel
        close = data["Close"] if "Close" in data.columns else data

        # Mapeia de volta para ticker interno
        for internal, yf_sym in ticker_map.items():
            try:
                if len(yf_tickers) == 1:
                    price = float(close.iloc[-1])
                else:
                    price = float(close[yf_sym].dropna().iloc[-1])
                results[internal] = price
            except Exception as e:
                logger.warning(f"yfinance: preco nao encontrado para {yf_sym}: {e}")

    except Exception as e:
        logger.error(f"yfinance download error: {e}")

    return results


async def fetch_international_quotes(
    tickers: list[str],
    asset_types: dict[str, str],
) -> dict[str, float]:
    """
    tickers:     lista de tickers internos
    asset_types: {ticker: asset_type}
    Retorna {ticker: preco_em_usd}.
    """
    ticker_map = {
        t: _ticker_to_yf(t, asset_types.get(t, ""))
        for t in tickers
    }

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        results = await loop.run_in_executor(pool, _fetch_prices_sync, ticker_map)

    return results
