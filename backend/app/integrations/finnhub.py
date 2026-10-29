"""Integracao Finnhub Stock API.

Endpoint utilizado:
  /quote?symbol={ticker} - Cotacao em tempo real de acoes e ETFs internacionais
  /stock/profile2 - Perfil da empresa, setor, pais, moeda e valor de mercado
  /stock/metric - Multiplos de valuation e rentabilidade (P/L, P/VP, ROE, Margem)
  /stock/recommendation - Consenso de analistas de Wall Street

Plano gratuito:
  - 60 chamadas por minuto (1 req/s).
  - Rate limiter dedicado: finnhub_limiter.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

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


async def fetch_finnhub_profile(ticker: str) -> Optional[dict[str, Any]]:
    """Consulta perfil empresarial de ativo internacional (/stock/profile2)."""
    key = _api_key()
    if not key:
        return None

    clean_ticker = (ticker or "").strip().upper()
    if not clean_ticker:
        return None

    url = f"{_BASE_URL}/stock/profile2"
    headers = {"X-Finnhub-Token": key}
    params = {"symbol": clean_ticker}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if isinstance(data, dict) and data.get("name"):
                market_cap = data.get("marketCapitalization")
                market_cap_val = float(market_cap) * 1_000_000.0 if isinstance(market_cap, (int, float)) else None
                return {
                    "country": data.get("country"),
                    "currency": data.get("currency"),
                    "exchange": data.get("exchange"),
                    "industry": data.get("finnhubIndustry"),
                    "ipo": data.get("ipo"),
                    "logo": data.get("logo"),
                    "market_cap": market_cap_val,
                    "name": data.get("name"),
                    "ticker": data.get("ticker") or clean_ticker,
                    "weburl": data.get("weburl"),
                }
    except Exception as exc:
        logger.warning(
            "[finnhub] Erro ao consultar perfil de %s: %s",
            sanitize_log_value(clean_ticker),
            sanitize_log_value(exc),
        )
    return None


async def fetch_finnhub_metrics(ticker: str) -> Optional[dict[str, Any]]:
    """Consulta metricas e multiplos fundamentalistas (/stock/metric)."""
    key = _api_key()
    if not key:
        return None

    clean_ticker = (ticker or "").strip().upper()
    if not clean_ticker:
        return None

    url = f"{_BASE_URL}/stock/metric"
    headers = {"X-Finnhub-Token": key}
    params = {"symbol": clean_ticker, "metric": "all"}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if isinstance(data, dict):
                metric_raw = data.get("metric")
                m: dict[str, Any] = metric_raw if isinstance(metric_raw, dict) else {}
                if not m:
                    return None

                def _flt(val: Any) -> Optional[float]:
                    return float(val) if isinstance(val, (int, float)) else None

                return {
                    "pe": _flt(m.get("peTTM") or m.get("peNormalizedAnnual")),
                    "pb": _flt(m.get("pbAnnual") or m.get("pbNormalizedAnnual")),
                    "dividend_yield": _flt(m.get("dividendYieldIndicatedAnnual")),
                    "roe": _flt(m.get("roeTTM") or m.get("roeRfy")),
                    "roa": _flt(m.get("roaTTM") or m.get("roaRfy")),
                    "net_margin": _flt(m.get("netProfitMarginTTM")),
                    "operating_margin": _flt(m.get("operatingMarginTTM")),
                    "eps": _flt(m.get("epsTTM") or m.get("epsNormalizedAnnual")),
                    "beta": _flt(m.get("beta")),
                    "week_52_high": _flt(m.get("52WeekHigh")),
                    "week_52_low": _flt(m.get("52WeekLow")),
                }
    except Exception as exc:
        logger.warning(
            "[finnhub] Erro ao consultar metricas de %s: %s",
            sanitize_log_value(clean_ticker),
            sanitize_log_value(exc),
        )
    return None


async def fetch_finnhub_recommendations(ticker: str) -> Optional[dict[str, Any]]:
    """Consulta consenso e recomendacoes de analistas (/stock/recommendation)."""
    key = _api_key()
    if not key:
        return None

    clean_ticker = (ticker or "").strip().upper()
    if not clean_ticker:
        return None

    url = f"{_BASE_URL}/stock/recommendation"
    headers = {"X-Finnhub-Token": key}
    params = {"symbol": clean_ticker}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                rec_raw = data[0]
                rec: dict[str, Any] = rec_raw if isinstance(rec_raw, dict) else {}
                strong_buy = int(rec.get("strongBuy") or 0)
                buy = int(rec.get("buy") or 0)
                hold = int(rec.get("hold") or 0)
                sell = int(rec.get("sell") or 0)
                strong_sell = int(rec.get("strongSell") or 0)
                total = strong_buy + buy + hold + sell + strong_sell

                consensus = "HOLD"
                if total > 0:
                    score = (strong_buy * 2 + buy * 1 + hold * 0 - sell * 1 - strong_sell * 2) / total
                    if score >= 0.6:
                        consensus = "STRONG_BUY"
                    elif score >= 0.2:
                        consensus = "BUY"
                    elif score <= -0.6:
                        consensus = "STRONG_SELL"
                    elif score <= -0.2:
                        consensus = "SELL"

                return {
                    "strong_buy": strong_buy,
                    "buy": buy,
                    "hold": hold,
                    "sell": sell,
                    "strong_sell": strong_sell,
                    "total_analysts": total,
                    "period": rec.get("period"),
                    "consensus": consensus,
                }
    except Exception as exc:
        logger.warning(
            "[finnhub] Erro ao consultar recomendacoes de %s: %s",
            sanitize_log_value(clean_ticker),
            sanitize_log_value(exc),
        )
    return None


async def fetch_finnhub_enrichment(ticker: str) -> Optional[dict[str, Any]]:
    """Obtem simultaneamente perfil, metricas e recomendacoes para enriquecimento."""
    clean_ticker = (ticker or "").strip().upper()
    if not clean_ticker or not _is_configured():
        return None

    results: list[Any] = await asyncio.gather(
        fetch_finnhub_profile(clean_ticker),
        fetch_finnhub_metrics(clean_ticker),
        fetch_finnhub_recommendations(clean_ticker),
        return_exceptions=True,
    )

    raw_profile = results[0] if len(results) > 0 else None
    raw_metrics = results[1] if len(results) > 1 else None
    raw_recs = results[2] if len(results) > 2 else None

    profile_dict: Optional[dict[str, Any]] = raw_profile if isinstance(raw_profile, dict) else None
    metrics_dict: Optional[dict[str, Any]] = raw_metrics if isinstance(raw_metrics, dict) else None
    recs_dict: Optional[dict[str, Any]] = raw_recs if isinstance(raw_recs, dict) else None

    if not profile_dict and not metrics_dict:
        return None

    return {
        "profile": profile_dict,
        "metrics": metrics_dict,
        "recommendations": recs_dict,
    }
