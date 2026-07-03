"""
Integracao Alpha Vantage.

Endpoints utilizados:
  GLOBAL_QUOTE        - cotacao atual de um ativo internacional
  TIME_SERIES_DAILY   - historico diario (compact = 100 dias, full = ~20 anos)

Economia de requests:
  - Historico so e buscado quando o banco nao tem dados ou o ultimo registro
    tem mais de 1 dia. Na primeira importacao (full) usa 1 request por ticker.
    Nos dias seguintes usa compact (1 request/dia/ticker).
  - Cotacao atual: 1 request por ciclo do scheduler (default 30min).

Rate limiter dedicado: alpha_vantage_limiter.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.alphavantage.co/query"
_TIMEOUT = 15.0


def _api_key() -> Optional[str]:
    return getattr(settings, "ALPHA_VANTAGE_API_KEY", None) or None


def _is_configured() -> bool:
    key = _api_key()
    return bool(key and key.strip() and key.strip().lower() != "demo")


def _sanitize_provider_message(message: str) -> str:
    """Remove chaves e tokens que alguns provedores ecoam em mensagens de limite."""
    if not message:
        return ""
    key = _api_key()
    clean = str(message)
    if key:
        clean = clean.replace(key, "***")
    clean = re.sub(r"API key as [A-Za-z0-9_-]+", "API key as ***", clean, flags=re.IGNORECASE)
    clean = re.sub(r"apikey[=:]\s*[A-Za-z0-9_-]+", "apikey=***", clean, flags=re.IGNORECASE)
    return clean


async def fetch_global_quote(ticker: str) -> Optional[float]:
    """
    Retorna o preco atual (previousClose ou price) de um ativo via GLOBAL_QUOTE.
    Retorna None se a API key nao estiver configurada ou se o ticker nao for encontrado.
    """
    if not _is_configured():
        logger.debug("[alpha_vantage] ALPHA_VANTAGE_API_KEY nao configurada — pulando")
        return None

    params = {"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": _api_key()}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        quote = data.get("Global Quote", {})
        if not quote:
            note = _sanitize_provider_message(data.get("Note") or data.get("Information") or "")
            if note:
                logger.warning("[alpha_vantage] GLOBAL_QUOTE %s: %s", ticker, note[:160])
            else:
                logger.warning("[alpha_vantage] GLOBAL_QUOTE %s: resposta vazia", ticker)
            return None

        price_str = quote.get("05. price") or quote.get("08. previous close")
        if not price_str:
            logger.warning("[alpha_vantage] GLOBAL_QUOTE %s: campo price ausente", ticker)
            return None

        price = float(price_str)
        logger.debug("[alpha_vantage] GLOBAL_QUOTE %s = %.4f", ticker, price)
        return price

    except Exception as e:
        logger.warning("[alpha_vantage] fetch_global_quote %s erro: %s", ticker, _sanitize_provider_message(str(e)))
        return None


async def fetch_daily_history(ticker: str, days_back: int = 100) -> list[tuple[datetime, float]]:
    """
    Retorna historico diario de fechamento para o ticker.
    """
    if not _is_configured():
        logger.debug("[alpha_vantage] ALPHA_VANTAGE_API_KEY nao configurada — pulando")
        return []

    output_size = "compact" if days_back <= 100 else "full"
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": output_size,
        "apikey": _api_key(),
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        note = _sanitize_provider_message(data.get("Note") or data.get("Information") or "")
        if note:
            logger.warning("[alpha_vantage] TIME_SERIES_DAILY %s: %s", ticker, note[:160])
            return []

        series = data.get("Time Series (Daily)", {})
        if not series:
            logger.warning("[alpha_vantage] TIME_SERIES_DAILY %s: serie vazia", ticker)
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        rows: list[tuple[datetime, float]] = []
        for date_str, ohlc in series.items():
            try:
                dt = datetime(
                    int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10]),
                    21, 0, 0, tzinfo=timezone.utc,
                )
                if dt < cutoff:
                    continue
                close = float(ohlc.get("4. close", 0))
                if close > 0:
                    rows.append((dt, close))
            except Exception:
                continue

        rows.sort(key=lambda x: x[0])
        logger.info("[alpha_vantage] TIME_SERIES_DAILY %s: %d registros (outputsize=%s)", ticker, len(rows), output_size)
        return rows

    except Exception as e:
        logger.warning("[alpha_vantage] fetch_daily_history %s erro: %s", ticker, _sanitize_provider_message(str(e)))
        return []
