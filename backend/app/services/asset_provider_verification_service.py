"""Serviço de verificação de existência de ativos nos provedores de mercado."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.core.log_safety import sanitize_log_value

logger = logging.getLogger(__name__)

_CRYPTO_SYNONYMS: dict[str, str] = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "TETHER": "USDT",
    "BINANCE COIN": "BNB",
    "BINANCECOIN": "BNB",
    "BNB": "BNB",
    "SOLANA": "SOL",
    "RIPPLE": "XRP",
    "CARDANO": "ADA",
    "DOGECOIN": "DOGE",
    "POLKADOT": "DOT",
    "AVALANCHE": "AVAX",
    "CHAINLINK": "LINK",
    "POLYGON": "MATIC",
    "SHIBA INU": "SHIB",
    "SHIBA": "SHIB",
    "LITECOIN": "LTC",
    "UNISWAP": "UNI",
    "STELLAR": "XLM",
    "MONERO": "XMR",
    "COSMOS": "ATOM",
    "BITCOIN CASH": "BCH",
    "USD COIN": "USDC",
}


async def verify_market_asset_exists(
    ticker: str,
    asset_type: str,
) -> tuple[bool, Optional[str]]:
    """Consulta provedores oficiais/externos para verificar se o ativo realmente existe.

    Retorna (existe: bool, nome_oficial: str | None).
    """
    normalized_ticker = ticker.strip().upper()
    normalized_type = str(asset_type).strip().upper()

    # Renda Fixa privada é produto contratual/bancário local
    if normalized_type == "RENDA_FIXA":
        return True, ticker

    # Tesouro Direto é estritamente controlado pelo catálogo oficial já existente
    if normalized_type == "TESOURO_DIRETO":
        from app.integrations.brapi import _TREASURY_NAME_MAP, _TREASURY_SLUG_RE
        lowered = normalized_ticker.lower()
        if (
            normalized_ticker in _TREASURY_NAME_MAP
            or lowered in _TREASURY_NAME_MAP.values()
            or _TREASURY_SLUG_RE.match(lowered)
            or normalized_ticker.startswith("TESOURO")
            or normalized_ticker.startswith("NTN-")
            or normalized_ticker.startswith("LTN-")
            or normalized_ticker.startswith("LFT-")
        ):
            return True, normalized_ticker
        return False, None

    # Ativos B3: consultar BRAPI
    if normalized_type in {"ACAO", "FII", "ETF_NACIONAL", "BDR"}:
        from app.integrations.brapi import fetch_asset_info, fetch_ticker_suggestions

        try:
            info = await fetch_asset_info(normalized_ticker)
            if info and isinstance(info, dict):
                symbol = str(info.get("symbol") or "").strip().upper()
                if symbol == normalized_ticker or normalized_ticker in symbol:
                    name = info.get("longName") or info.get("shortName") or normalized_ticker
                    return True, name
        except Exception as exc:
            logger.warning("[verify_asset] erro ao consultar BRAPI quote para %s: %s", sanitize_log_value(normalized_ticker), sanitize_log_value(exc))

        # Fallback para B3: verificar lista de tickers se quote falhar
        try:
            suggestions = await fetch_ticker_suggestions(normalized_ticker, limit=5)
            for item in suggestions:
                if isinstance(item, dict) and str(item.get("stock") or "").strip().upper() == normalized_ticker:
                    name = item.get("name") or normalized_ticker
                    return True, name
        except Exception as exc:
            logger.warning("[verify_asset] erro ao consultar sugestoes BRAPI para %s: %s", sanitize_log_value(normalized_ticker), sanitize_log_value(exc))

        # Fallback 2 para B3: Yahoo Finance (.SA) se BRAPI falhar ou nao tiver credencial
        def _check_yahoo_b3() -> tuple[bool, Optional[str]]:
            try:
                import yfinance as yf
                t = yf.Ticker(f"{normalized_ticker}.SA")
                price = getattr(t.fast_info, "last_price", None)
                if price is not None:
                    name = t.info.get("shortName") or t.info.get("longName") or normalized_ticker
                    return True, name
            except Exception:
                pass
            return False, None

        try:
            exists, yf_name = await asyncio.to_thread(_check_yahoo_b3)
            if exists:
                return True, yf_name
        except Exception as exc:
            logger.warning("[verify_asset] erro ao consultar yfinance para B3 %s: %s", sanitize_log_value(normalized_ticker), sanitize_log_value(exc))

        return False, None

    # Ativos Internacionais: Stocks e ETFs
    if normalized_type in {"STOCK", "ETF_INTERNACIONAL"}:
        from app.integrations.brapi import fetch_asset_info

        # 1. Tentar via BRAPI primeiro
        try:
            info = await fetch_asset_info(normalized_ticker)
            if info and isinstance(info, dict):
                name = info.get("longName") or info.get("shortName") or normalized_ticker
                return True, name
        except Exception:
            pass

        # 2. Tentar via Yahoo Finance
        def _check_yahoo() -> tuple[bool, Optional[str]]:
            try:
                import yfinance as yf
                t = yf.Ticker(normalized_ticker)
                price = getattr(t.fast_info, "last_price", None)
                if price is not None:
                    name = t.info.get("shortName") or t.info.get("longName") or normalized_ticker
                    return True, name
            except Exception:
                pass
            return False, None

        try:
            exists, yf_name = await asyncio.to_thread(_check_yahoo)
            if exists:
                return True, yf_name
        except Exception as exc:
            logger.warning("[verify_asset] erro ao consultar yfinance para %s: %s", sanitize_log_value(normalized_ticker), sanitize_log_value(exc))

        return False, None

    # Criptomoedas
    if normalized_type == "CRIPTO":
        resolved_ticker = _CRYPTO_SYNONYMS.get(normalized_ticker, normalized_ticker)
        from app.integrations.brapi import fetch_crypto_quote

        try:
            quotes = await fetch_crypto_quote([resolved_ticker])
            if quotes and (resolved_ticker in quotes or quotes.get(resolved_ticker) is not None):
                return True, resolved_ticker
        except Exception as exc:
            logger.warning("[verify_asset] erro ao consultar BRAPI crypto para %s: %s", sanitize_log_value(resolved_ticker), sanitize_log_value(exc))

        # Fallback para Yahoo Finance crypto: {TICKER}-USD
        def _check_yahoo_crypto() -> tuple[bool, Optional[str]]:
            try:
                import yfinance as yf
                t = yf.Ticker(f"{resolved_ticker}-USD")
                price = getattr(t.fast_info, "last_price", None)
                if price is not None:
                    name = t.info.get("shortName") or t.info.get("longName") or resolved_ticker
                    return True, name
            except Exception:
                pass
            return False, None

        try:
            exists, yf_name = await asyncio.to_thread(_check_yahoo_crypto)
            if exists:
                return True, yf_name
        except Exception as exc:
            logger.warning("[verify_asset] erro ao consultar yfinance crypto para %s: %s", sanitize_log_value(resolved_ticker), sanitize_log_value(exc))

        return False, None

    return False, None
