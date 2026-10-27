"""Integracao Finnhub Stock API.

Endpoint utilizado:
  /quote?symbol={ticker} - Cotacao em tempo real de acoes e ETFs internacionais

Plano gratuito:
  - 60 chamadas por minuto (1 req/s).
  - Rate limiter dedicado: finnhub_limiter.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.core.log_safety import sanitize_log_value

logger = logging.getLogger(__name__)

_BASE_URL = "https://finnhub.io/api/v1"
_TIMEOUT = 15.0


def _api_key() -> Optional[str]:
    return getattr(settings, "FINNHUB_API_KEY", None) or None


def _is_configured() -> bool:
    key = _api_key()
    return bool(key and key.strip())


async def fetch_finnhub_quote(ticker: str) -> Optional[float]:
    """Retorna o preco atual (c) de um ativo internacional via Finnhub.

    Retorna None se a API key nao estiver configurada, se o ticker nao for
    encontrado ou em caso de erro na requisicao.
    """
    key = _api_key()
    if not key:
        logger.debug("[finnhub] FINNHUB_API_KEY nao configurada — pulando")
        return None

    clean_ticker = (ticker or "").strip().upper()
    if not clean_ticker:
        return None

    url = f"{_BASE_URL}/quote"
    headers = {"X-Finnhub-Token": key}
    params = {"symbol": clean_ticker}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 429:
                logger.warning("[finnhub] Limite de requisicoes atingido (HTTP 429)")
                return None
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, dict):
                current_price = data.get("c")
                if current_price is not None and isinstance(current_price, (int, float)) and current_price > 0:
                    return float(current_price)
                prev_close = data.get("pc")
                if prev_close is not None and isinstance(prev_close, (int, float)) and prev_close > 0:
                    return float(prev_close)
    except Exception as exc:
        logger.warning(
            "[finnhub] Erro ao consultar cotacao de %s: %s",
            sanitize_log_value(clean_ticker),
            sanitize_log_value(exc),
        )
    return None
