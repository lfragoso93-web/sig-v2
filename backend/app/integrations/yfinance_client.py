import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)


def get_ticker_info(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return info or {}
    except Exception as e:
        logger.error(f"Erro ao buscar info de {ticker}: {e}")
        return {}


def get_current_price(ticker: str) -> float | None:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.error(f"Erro ao buscar preço de {ticker}: {e}")
        return None


def get_price_history(
    ticker: str,
    start: date | None = None,
    end: date | None = None,
    period: str = "1y",
) -> pd.DataFrame:
    try:
        t = yf.Ticker(ticker)
        if start and end:
            hist = t.history(
                start=datetime.combine(start, datetime.min.time()),
                end=datetime.combine(end, datetime.min.time()),
            )
        else:
            hist = t.history(period=period)
        return hist
    except Exception as e:
        logger.error(f"Erro ao buscar histórico de {ticker}: {e}")
        return pd.DataFrame()


def get_dividends(ticker: str) -> pd.Series:
    try:
        t = yf.Ticker(ticker)
        return t.dividends
    except Exception as e:
        logger.error(f"Erro ao buscar dividendos de {ticker}: {e}")
        return pd.Series(dtype=float)
