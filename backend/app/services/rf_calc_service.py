"""
rf_calc_service.py

Calcula o valor atual estimado de posicoes de Renda Fixa usando o
historico real de taxas armazenado na tabela rate_history (BCB).

Logica de calculo:
  Para cada aporte (transacao de compra):
    1. Busca as taxas diarias do periodo [data_aporte, hoje] no banco.
    2. Calcula o fator acumulado real: PROD(1 + taxa_diaria_i / 100)
    3. valor_atual_aporte = valor_aporte * fator_acumulado
  current_value = soma dos valores atualizados de todos os aportes.

Indexadores suportados (extraidos do campo `notes`):
  - CDI_PCT  : "110% do CDI", "100% CDI"
  - CDI_PLUS : "CDI + 2%"
  - IPCA_PLUS: "IPCA + 5%"
  - PREFIXADO: "12% a.a."

Fallback (quando banco nao tem dados do periodo):
  Usa taxa anual corrente da BRAPI ou constante conservadora.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
from app.db.session import async_session_factory

log = logging.getLogger(__name__)

_CACHE_TTL = 3600
_RF_TYPES = {"RENDA_FIXA"}
_FALLBACK_CDI_ANNUAL = 10.5
_FALLBACK_IPCA_ANNUAL = 5.0
BRAPI_BASE = "https://brapi.dev/api"


# ---------------------------------------------------------------------------
# Parser de notas (inalterado)
# ---------------------------------------------------------------------------

class RFParams:
    def __init__(self, indexer: str, rate: float = 0.0, spread: float = 0.0):
        self.indexer = indexer
        self.rate = rate
        self.spread = spread

    def __repr__(self) -> str:  # pragma: no cover
        return f"RFParams(indexer={self.indexer!r}, rate={self.rate}, spread={self.spread})"


def parse_rf_notes(notes: Optional[str]) -> RFParams:
    if not notes:
        return RFParams("UNKNOWN")
    n = notes.strip()
    m = re.search(r"CDI\s*\+\s*([0-9]+(?:[.,][0-9]+)?)", n, re.IGNORECASE)
    if m:
        return RFParams("CDI_PLUS", spread=float(m.group(1).replace(",", ".")))
    m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*%\s*(?:do\s+)?CDI", n, re.IGNORECASE)
    if m:
        return RFParams("CDI_PCT", rate=float(m.group(1).replace(",", ".")))
    if re.search(r"\bCDI\b", n, re.IGNORECASE):
        return RFParams("CDI_PCT", rate=100.0)
    m = re.search(r"IPCA\s*\+\s*([0-9]+(?:[.,][0-9]+)?)", n, re.IGNORECASE)
    if m:
        return RFParams("IPCA_PLUS", spread=float(m.group(1).replace(",", ".")))
    if re.search(r"\bIPCA\b", n, re.IGNORECASE):
        return RFParams("IPCA_PLUS", spread=0.0)
    m = re.search(
        r"(?:prefixado[\s:]*)?([0-9]+(?:[.,][0-9]+)?)\s*%(?:\s*a\.?a\.?)?",
        n, re.IGNORECASE,
    )
    if m:
        return RFParams("PREFIXADO", rate=float(m.group(1).replace(",", ".")))
    return RFParams("UNKNOWN")


# ---------------------------------------------------------------------------
# Busca de fator acumulado no banco (historico real)
# ---------------------------------------------------------------------------

FATOR_SQL = text("""
    SELECT rate_daily
    FROM   rate_history
    WHERE  indicator = :indicator
      AND  date >= :start_date
      AND  date <= :end_date
    ORDER  BY date ASC
""")


async def _accumulated_factor_from_db(
    indicator: str,
    start_date: date,
    end_date: date,
    spread_annual: float = 0.0,
    pct_of_base: float = 100.0,
) -> Optional[float]:
    """
    Calcula o fator acumulado real usando o historico diario do banco.

    Para CDI_PCT: aplica pct_of_base% da taxa diaria em cada dia.
    Para CDI_PLUS / IPCA_PLUS: adiciona spread convertido para diario.

    Retorna None se nao houver dados suficientes no banco.
    """
    if start_date >= end_date:
        return 1.0

    cache_key = (
        f"rf_factor:{indicator}:{start_date}:{end_date}"
        f":pct={pct_of_base}:spread={spread_annual}"
    )
    cached = await cache_get(cache_key)
    if cached is not None:
        return float(cached)

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                FATOR_SQL,
                {"indicator": indicator, "start_date": start_date, "end_date": end_date},
            )
            rows = result.fetchall()
    except Exception as e:
        log.warning("[rf_calc] DB query falhou para %s [%s, %s]: %s", indicator, start_date, end_date, e)
        return None

    if not rows:
        log.debug("[rf_calc] Sem dados no banco para %s [%s, %s]", indicator, start_date, end_date)
        return None

    # Converte spread anual para diario: (1 + s/100)^(1/252) - 1
    spread_daily = 0.0
    if spread_annual > 0:
        spread_daily = ((1 + spread_annual / 100) ** (1 / 252) - 1) * 100

    factor = 1.0
    for row in rows:
        daily_base = float(row[0])  # % a.d. do indicador
        # Aplica percentual do CDI se necessario
        effective_daily = daily_base * (pct_of_base / 100.0) + spread_daily
        factor *= (1 + effective_daily / 100)

    # Cache por 1h (hoje) ou 24h (periodo no passado)
    ttl = _CACHE_TTL if end_date >= date.today() else 86400
    await cache_set(cache_key, factor, ttl=ttl)
    return factor


# ---------------------------------------------------------------------------
# Fallback: taxa corrente via BRAPI
# ---------------------------------------------------------------------------

async def _fetch_brapi_indicator(key: str) -> Optional[float]:
    cache_key = f"brapi_indicator:{key}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return float(cached)
    try:
        import os
        token = os.getenv("BRAPI_TOKEN", "")
        params: dict = {"key": key}
        if token:
            params["token"] = token
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(f"{BRAPI_BASE}/v2/finance", params=params)
            resp.raise_for_status()
            data = resp.json()
        for item in data.get("finance", []):
            if str(item.get("key", "")).upper() == key.upper():
                annual = item.get("annual") or item.get("yearly")
                if annual:
                    val = float(str(annual).replace(",", "."))
                    await cache_set(cache_key, val, ttl=_CACHE_TTL)
                    return val
                monthly = item.get("monthly")
                if monthly:
                    m = float(str(monthly).replace(",", "."))
                    val = ((1 + m / 100) ** 12 - 1) * 100
                    await cache_set(cache_key, val, ttl=_CACHE_TTL)
                    return val
    except Exception as e:
        log.warning("[rf_calc] BRAPI %s falhou: %s", key, e)
    return None


async def _fallback_factor_annual(
    annual_pct: float,
    start_date: date,
    end_date: date,
) -> float:
    """Fator de crescimento usando taxa anual fixa como fallback."""
    days = max(0, (end_date - start_date).days)
    if days == 0:
        return 1.0
    return (1 + annual_pct / 100) ** (days / 252)


async def _get_annual_rate(indicator: str, default: float) -> float:
    val = await _fetch_brapi_indicator(indicator)
    return val if val is not None else default


# ---------------------------------------------------------------------------
# Calculo por aporte
# ---------------------------------------------------------------------------

async def _estimate_aporte(
    value: float,
    start_date: date,
    params: RFParams,
) -> float:
    """
    Calcula o valor atual de um unico aporte usando historico do banco.
    Usa fallback anual se o banco nao tiver dados suficientes.
    """
    end_date = date.today()
    if start_date >= end_date or value <= 0:
        return value

    factor: Optional[float] = None

    if params.indexer == "CDI_PCT":
        factor = await _accumulated_factor_from_db(
            "CDI", start_date, end_date,
            pct_of_base=params.rate,
        )
        if factor is None:
            annual = await _get_annual_rate("CDI", _FALLBACK_CDI_ANNUAL)
            effective = annual * (params.rate / 100.0)
            factor = await _fallback_factor_annual(effective, start_date, end_date)

    elif params.indexer == "CDI_PLUS":
        factor = await _accumulated_factor_from_db(
            "CDI", start_date, end_date,
            spread_annual=params.spread,
        )
        if factor is None:
            annual = await _get_annual_rate("CDI", _FALLBACK_CDI_ANNUAL)
            factor = await _fallback_factor_annual(annual + params.spread, start_date, end_date)

    elif params.indexer == "IPCA_PLUS":
        factor = await _accumulated_factor_from_db(
            "IPCA", start_date, end_date,
            spread_annual=params.spread,
        )
        if factor is None:
            annual = await _get_annual_rate("IPCA", _FALLBACK_IPCA_ANNUAL)
            factor = await _fallback_factor_annual(annual + params.spread, start_date, end_date)

    elif params.indexer == "PREFIXADO":
        # Prefixado nao precisa de banco: taxa ja esta em notes
        factor = await _fallback_factor_annual(params.rate, start_date, end_date)

    if factor is None or factor < 1.0:
        factor = 1.0

    return round(value * factor, 8)


# ---------------------------------------------------------------------------
# Interface principal
# ---------------------------------------------------------------------------

async def enrich_rf_positions(
    positions: list[dict],
    transactions_by_ticker: dict[str, list],
) -> dict[str, float]:
    """
    Calcula current_value estimado para cada posicao de RENDA_FIXA.
    Usa fator acumulado real do banco (rate_history) por aporte individual.
    """
    result: dict[str, float] = {}

    for pos in positions:
        if str(pos.get("asset_type", "")).upper() not in _RF_TYPES:
            continue

        ticker = pos["ticker"]
        txs = transactions_by_ticker.get(ticker, [])
        if not txs:
            continue

        txs_sorted = sorted(txs, key=lambda t: (t.date, t.id))
        buy_txs = [t for t in txs_sorted if str(getattr(t, "operation", "")).lower() in ("buy", "compra")]
        sell_txs = [t for t in txs_sorted if str(getattr(t, "operation", "")).lower() in ("sell", "venda")]

        if not buy_txs:
            continue

        # Indexador: usa notes da compra mais recente com notes preenchido
        notes = None
        for tx in reversed(buy_txs):
            if getattr(tx, "notes", None):
                notes = tx.notes
                break

        params = parse_rf_notes(notes)
        if params.indexer == "UNKNOWN":
            log.debug("[rf_calc] %s sem indexador em notes=%r — pulando", ticker, notes)
            continue

        # Aportes: (date, valor_brl)
        aportes: list[tuple[date, float]] = []
        total_aportado = 0.0
        for tx in buy_txs:
            qty = float(tx.quantity or 0)
            price = float(tx.price or 0)
            fees = float(tx.fees or 0)
            val = qty * price + fees
            if val > 0:
                aportes.append((tx.date, val))
                total_aportado += val

        if not aportes or total_aportado <= 0:
            continue

        # Ratio restante apos vendas
        total_vendido = sum(
            float(t.quantity or 0) * float(t.price or 0) for t in sell_txs
        )
        ratio_restante = max(0.0, (total_aportado - total_vendido) / total_aportado)
        if ratio_restante <= 0:
            continue

        # Soma valor atualizado de cada aporte
        current_value_total = 0.0
        for tx_date, valor_aporte in aportes:
            valor_restante = valor_aporte * ratio_restante
            try:
                valor_atual = await _estimate_aporte(valor_restante, tx_date, params)
                current_value_total += valor_atual
            except Exception as e:
                log.warning("[rf_calc] erro aporte %s em %s: %s", ticker, tx_date, e)
                current_value_total += valor_restante

        result[ticker] = round(current_value_total, 2)
        log.debug(
            "[rf_calc] %s | aportes=%d | ratio=%.4f | indexer=%s | current=%.2f",
            ticker, len(aportes), ratio_restante, params.indexer, result[ticker],
        )

    return result
