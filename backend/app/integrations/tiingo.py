"""Integracao Tiingo API.

Endpoints utilizados:
  /iex/{ticker} - Cotacao em tempo real/IEX (last, tngoLast, prevClose)
  /tiingo/daily/{ticker}/prices - Precos historicos auditados EOD (adjClose, close)

Plano gratuito:
  - 500 chamadas por dia (50 req/hora).
  - Rate limiter dedicado: tiingo_limiter.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.core.log_safety import sanitize_log_value

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.tiingo.com"
_TIMEOUT = 15.0


def _api_key() -> Optional[str]:
    return getattr(settings, "TIINGO_API_KEY", None) or None


def _is_configured() -> bool:
    key = _api_key()
    return bool(key and key.strip())


async def fetch_tiingo_quote(ticker: str) -> Optional[float]:
    """Retorna o preco atual ou fechamento recente de um ativo internacional via Tiingo.

    Tenta primeiramente a cotacao em tempo real IEX; caso nao disponivel (ex: fora
    do horario de pregao), consulta o ultimo fechamento ajustado diario.
    Retorna None se a chave nao estiver configurada ou se o ticker nao existir.
    """
    if not _is_configured():
        logger.debug("[tiingo] TIINGO_API_KEY nao configurada — pulando")
        return None

    clean_ticker = (ticker or "").strip().lower()
    if not clean_ticker:
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {_api_key()}",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            # 1. Tentar cotacao IEX
            iex_url = f"{_BASE_URL}/iex/{clean_ticker}"
            resp = await client.get(iex_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    item = data[0]
                    last = item.get("last") or item.get("tngoLast") or item.get("prevClose")
                    if last is not None and isinstance(last, (int, float)) and last > 0:
                        return float(last)
                elif isinstance(data, dict):
                    last = data.get("last") or data.get("tngoLast") or data.get("prevClose")
                    if last is not None and isinstance(last, (int, float)) and last > 0:
                        return float(last)

            # 2. Fallback para fechamento diario EOD
            daily_url = f"{_BASE_URL}/tiingo/daily/{clean_ticker}/prices"
            params = {"sort": "-date", "columns": "adjClose,close"}
            resp_daily = await client.get(daily_url, headers=headers, params=params)
            if resp_daily.status_code == 200:
                daily_data = resp_daily.json()
                if isinstance(daily_data, list) and daily_data:
                    first_bar = daily_data[0]
                    price = first_bar.get("adjClose") or first_bar.get("close")
                    if price is not None and isinstance(price, (int, float)) and price > 0:
                        return float(price)
    except Exception as exc:
        logger.warning(
            "[tiingo] Erro ao consultar cotacao de %s: %s",
            sanitize_log_value(clean_ticker),
            sanitize_log_value(exc),
        )
    return None
