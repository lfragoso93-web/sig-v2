"""Histórico de criptomoedas via BRAPI v2.

Adapter pequeno e isolado para o endpoint ``/api/v2/crypto``. A BRAPI é a fonte
primária quando o token/plano disponível permite histórico; o chamador decide o
fallback quando a fonte estiver indisponível, não autorizada ou retornar vazio.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.core.config import settings

_BRAPI_CRYPTO_URL = "https://brapi.dev/api/v2/crypto"

_CRYPTO_NAME_MAP = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "CARDANO": "ADA",
    "SOLANA": "SOL",
    "RIPPLE": "XRP",
}


def normalize_crypto_code(value: str) -> str:
    raw = str(value or "").strip().upper()
    raw = _CRYPTO_NAME_MAP.get(raw, raw)
    for separator in ("-", "/"):
        if separator in raw:
            raw = raw.split(separator, 1)[0]
    for suffix in ("USDT", "USDC", "BRL", "USD", "EUR", "GBP"):
        if raw.endswith(suffix) and len(raw) > len(suffix):
            raw = raw[: -len(suffix)]
            break
    return raw


def _auth_headers() -> dict[str, str]:
    token = str(getattr(settings, "BRAPI_TOKEN", "") or "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _parse_history(payload: object) -> list[tuple[datetime, float]]:
    if not isinstance(payload, dict):
        return []
    results = payload.get("results") or payload.get("coins") or []
    if not isinstance(results, list) or not results:
        return []
    item = results[0] if isinstance(results[0], dict) else {}
    history = (
        item.get("historicalDataPrice")
        or item.get("historical")
        or item.get("history")
        or []
    )
    rows: list[tuple[datetime, float]] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        close = entry.get("adjclose") or entry.get("close") or entry.get("price") or entry.get("value")
        ts_raw = entry.get("date") or entry.get("timestamp")
        if close is None or ts_raw is None:
            continue
        try:
            if isinstance(ts_raw, (int, float)):
                ts = datetime.fromtimestamp(float(ts_raw), tz=timezone.utc)
            else:
                ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                else:
                    ts = ts.astimezone(timezone.utc)
            price = float(close)
        except (TypeError, ValueError, OverflowError):
            continue
        if price > 0:
            rows.append((ts, price))
    rows.sort(key=lambda item: item[0])
    return rows


async def fetch_brapi_crypto_history(
    ticker: str,
    *,
    currency: str = "USD",
    range_: str = "max",
    interval: str = "1d",
) -> list[tuple[datetime, float]]:
    """Busca histórico diário da BRAPI; falha HTTP fica a cargo do chamador."""
    code = normalize_crypto_code(ticker)
    if not code:
        return []
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.get(
            _BRAPI_CRYPTO_URL,
            headers=_auth_headers(),
            params={
                "coin": code,
                "currency": currency.upper(),
                "range": range_,
                "interval": interval,
            },
        )
        response.raise_for_status()
        return _parse_history(response.json())
