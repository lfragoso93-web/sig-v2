import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, date, timedelta

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
        logger.error(f"Erro ao buscar preco de {ticker}: {e}")
        return None


def get_price_history(
    ticker: str,
    start: date | None = None,
    end: date | None = None,
    period: str = "1y",
) -> pd.DataFrame:
    """
    Retorna o historico de precos do ticker.

    - Quando start e end sao informados, usa intervalo explicito.
      O yfinance trata `end` como exclusivo, por isso incrementamos
      +1 dia para garantir que o dia final seja incluido nos resultados.
    - Quando apenas `period` e informado, converte para start/end
      explicito pois yfinance nao aceita periodos arbitrarios (ex: '365d').
      Periodos validos aceitos diretamente: 1d, 5d, 1mo, 3mo, 6mo,
      1y, 2y, 5y, 10y, ytd, max.
    """
    _VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
    try:
        t = yf.Ticker(ticker)
        if start and end:
            # end e exclusivo no yfinance: adiciona +1 dia para incluir a data final
            end_inclusive = end + timedelta(days=1)
            hist = t.history(
                start=datetime.combine(start, datetime.min.time()),
                end=datetime.combine(end_inclusive, datetime.min.time()),
            )
        elif period in _VALID_PERIODS:
            hist = t.history(period=period)
        else:
            # Period invalido (ex: "365d"): converte para start/end explicito
            try:
                days = int(str(period).rstrip("d"))
            except (ValueError, AttributeError):
                days = 365
            calc_start = date.today() - timedelta(days=days)
            calc_end   = date.today() + timedelta(days=1)  # end exclusivo
            hist = t.history(
                start=datetime.combine(calc_start, datetime.min.time()),
                end=datetime.combine(calc_end, datetime.min.time()),
            )
        return hist
    except Exception as e:
        logger.error(f"Erro ao buscar historico de {ticker}: {e}")
        return pd.DataFrame()


def get_dividends(ticker: str) -> pd.Series:
    try:
        t = yf.Ticker(ticker)
        return t.dividends
    except Exception as e:
        logger.error(f"Erro ao buscar dividendos de {ticker}: {e}")
        return pd.Series(dtype=float)
