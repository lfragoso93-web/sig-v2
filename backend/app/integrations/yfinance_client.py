import logging
import time
import threading
from datetime import datetime, date, timedelta

import yfinance as yf
import pandas as pd

from app.core.log_safety import sanitize_log_value

logger = logging.getLogger(__name__)

# Lock e intervalo mínimo compartilhados com price_history_service e quotes_service.
# Importados aqui para evitar dependência circular — price_history_service
# não importa yfinance_client, então a importação é segura neste sentido.
try:
    from app.services.price_history_service import _yf_thread_lock, _YF_MIN_INTERVAL, _yf_last_call
except ImportError:
    # Fallback caso este módulo seja usado standalone (testes, scripts)
    _yf_thread_lock = threading.Lock()
    _YF_MIN_INTERVAL = 12.0
    _yf_last_call = [0.0]


def _throttled_call(fn, *args):
    """
    Executa fn(*args) sob _yf_thread_lock com pausa mínima de _YF_MIN_INTERVAL
    entre chamadas. Centraliza o throttle de todas as chamadas yfinance do processo.
    """
    with _yf_thread_lock:
        elapsed = time.monotonic() - _yf_last_call[0]
        if elapsed < _YF_MIN_INTERVAL:
            time.sleep(_YF_MIN_INTERVAL - elapsed)
        try:
            return fn(*args)
        finally:
            _yf_last_call[0] = time.monotonic()


def get_ticker_info(ticker: str) -> dict:
    def _call():
        try:
            t = yf.Ticker(ticker)
            return t.info or {}
        except Exception as e:
            logger.error(
                "Erro ao buscar info de %s: %s",
                sanitize_log_value(ticker),
                sanitize_log_value(e),
            )
            return {}
    return _throttled_call(_call)


def get_current_price(ticker: str) -> float | None:
    def _call():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1d")
            if hist.empty:
                return None
            return float(hist["Close"].iloc[-1])
        except Exception as e:
            logger.error(
                "Erro ao buscar preco de %s: %s",
                sanitize_log_value(ticker),
                sanitize_log_value(e),
            )
            return None
    return _throttled_call(_call)


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

    def _call():
        try:
            t = yf.Ticker(ticker)
            if start and end:
                end_inclusive = end + timedelta(days=1)
                return t.history(
                    start=datetime.combine(start, datetime.min.time()),
                    end=datetime.combine(end_inclusive, datetime.min.time()),
                )
            elif period in _VALID_PERIODS:
                return t.history(period=period)
            else:
                try:
                    days = int(str(period).rstrip("d"))
                except (ValueError, AttributeError):
                    days = 365
                calc_start = date.today() - timedelta(days=days)
                calc_end   = date.today() + timedelta(days=1)
                return t.history(
                    start=datetime.combine(calc_start, datetime.min.time()),
                    end=datetime.combine(calc_end, datetime.min.time()),
                )
        except Exception as e:
            logger.error(
                "Erro ao buscar historico de %s: %s",
                sanitize_log_value(ticker),
                sanitize_log_value(e),
            )
            return pd.DataFrame()

    return _throttled_call(_call)


def get_dividends(ticker: str) -> pd.Series:
    def _call():
        try:
            t = yf.Ticker(ticker)
            return t.dividends
        except Exception as e:
            logger.error(
                "Erro ao buscar dividendos de %s: %s",
                sanitize_log_value(ticker),
                sanitize_log_value(e),
            )
            return pd.Series(dtype=float)
    return _throttled_call(_call)
