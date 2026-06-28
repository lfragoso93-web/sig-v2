"""
rf_calc_service.py

Calcula o valor atual estimado de posições de Renda Fixa com base nos
juros acumulados desde a data de aplicação.

Indexadores suportados (extraídos do campo `notes` da transação):
  - CDI percentual  : "110% do CDI", "100% CDI", "110%CDI"
  - CDI + spread    : "CDI + 2%", "CDI+1.5%"
  - IPCA + spread   : "IPCA + 5%", "IPCA+4.5% a.a."
  - Prefixado       : "12% a.a.", "12.5%", "prefixado 11%"

Fonte das taxas:
  - CDI acumulado  : endpoint BRAPI /v2/finance/calculate-cdi (ou indicadores)
  - IPCA acumulado : endpoint BRAPI /v2/finance/ipca (ou indicadores)
  - Fallback        : estimativas conservadoras fixas quando BRAPI indisponível
"""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Optional

import httpx

from app.core.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_CACHE_TTL = 3600  # 1h — taxas mudam pouco durante o dia
_RF_TYPES = {"RENDA_FIXA"}

# Taxas anuais de fallback (quando BRAPI indisponível)
_FALLBACK_CDI_ANNUAL = 10.5   # % a.a. aproximado
_FALLBACK_IPCA_ANNUAL = 5.0   # % a.a. aproximado

BRAPI_BASE = "https://brapi.dev/api"


# ---------------------------------------------------------------------------
# Parser de notas
# ---------------------------------------------------------------------------

class RFParams:
    """Parâmetros extraídos do campo `notes` de uma transação de RF."""

    def __init__(
        self,
        indexer: str,           # "CDI_PCT", "CDI_PLUS", "IPCA_PLUS", "PREFIXADO", "UNKNOWN"
        rate: float = 0.0,      # percentual CDI (ex: 110.0) ou spread/taxa a.a.
        spread: float = 0.0,    # spread sobre CDI ou IPCA em % a.a.
    ):
        self.indexer = indexer
        self.rate = rate
        self.spread = spread

    def __repr__(self) -> str:  # pragma: no cover
        return f"RFParams(indexer={self.indexer!r}, rate={self.rate}, spread={self.spread})"


def parse_rf_notes(notes: Optional[str]) -> RFParams:
    """
    Extrai indexador e taxas do campo `notes`.

    Exemplos reconhecidos:
      "110% do CDI"     -> CDI_PCT, rate=110.0
      "100% CDI"        -> CDI_PCT, rate=100.0
      "CDI + 2%"        -> CDI_PLUS, spread=2.0
      "CDI+1.5% a.a."   -> CDI_PLUS, spread=1.5
      "IPCA + 5% a.a."  -> IPCA_PLUS, spread=5.0
      "IPCA+4.5%"       -> IPCA_PLUS, spread=4.5
      "12% a.a."        -> PREFIXADO, rate=12.0
      "prefixado 11.5%" -> PREFIXADO, rate=11.5
      None / ""         -> UNKNOWN
    """
    if not notes:
        return RFParams("UNKNOWN")

    n = notes.strip()

    # CDI + spread: "CDI + 2%" ou "CDI+1.5% a.a."
    m = re.search(r"CDI\s*\+\s*([0-9]+(?:[.,][0-9]+)?)", n, re.IGNORECASE)
    if m:
        spread = float(m.group(1).replace(",", "."))
        return RFParams("CDI_PLUS", spread=spread)

    # X% do CDI ou X% CDI
    m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*%\s*(?:do\s+)?CDI", n, re.IGNORECASE)
    if m:
        rate = float(m.group(1).replace(",", "."))
        return RFParams("CDI_PCT", rate=rate)

    # CDI puro (sem spread, sem percentual explícito → assume 100%)
    if re.search(r"\bCDI\b", n, re.IGNORECASE):
        return RFParams("CDI_PCT", rate=100.0)

    # IPCA + spread: "IPCA + 5%" ou "IPCA+4.5% a.a."
    m = re.search(r"IPCA\s*\+\s*([0-9]+(?:[.,][0-9]+)?)", n, re.IGNORECASE)
    if m:
        spread = float(m.group(1).replace(",", "."))
        return RFParams("IPCA_PLUS", spread=spread)

    # IPCA puro
    if re.search(r"\bIPCA\b", n, re.IGNORECASE):
        return RFParams("IPCA_PLUS", spread=0.0)

    # Prefixado: "prefixado 12%" ou "12% a.a." ou simplesmente "12.5%"
    m = re.search(
        r"(?:prefixado[\s:]*)?([0-9]+(?:[.,][0-9]+)?)\s*%(?:\s*a\.?a\.?)?",
        n, re.IGNORECASE,
    )
    if m:
        rate = float(m.group(1).replace(",", "."))
        return RFParams("PREFIXADO", rate=rate)

    return RFParams("UNKNOWN")


# ---------------------------------------------------------------------------
# Busca de taxas acumuladas
# ---------------------------------------------------------------------------

async def _fetch_brapi_indicator(key: str) -> Optional[float]:
    """
    Busca indicador de mercado da BRAPI.
    Retorna a taxa anual atual (% a.a.) do indicador.
    """
    cache_key = f"brapi_indicator:{key}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return float(cached)

    try:
        import os
        token = os.getenv("BRAPI_TOKEN", "")
        url = f"{BRAPI_BASE}/v2/finance"
        params = {"key": key}
        if token:
            params["token"] = token

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        # Estrutura BRAPI: {"finance": [{"key": "CDI", "monthly": "0.88", ...}]}
        finance_list = data.get("finance", [])
        for item in finance_list:
            if str(item.get("key", "")).upper() == key.upper():
                # Tenta anual primeiro, depois mensal convertido
                annual = item.get("annual") or item.get("yearly")
                if annual is not None:
                    val = float(str(annual).replace(",", "."))
                    await cache_set(cache_key, val, ttl=_CACHE_TTL)
                    return val
                monthly = item.get("monthly")
                if monthly is not None:
                    m = float(str(monthly).replace(",", "."))
                    # (1 + m/100)^12 - 1
                    annual_est = ((1 + m / 100) ** 12 - 1) * 100
                    await cache_set(cache_key, annual_est, ttl=_CACHE_TTL)
                    return annual_est
    except Exception as e:
        logger.warning("[rf_calc] BRAPI indicator '%s' falhou: %s", key, e)

    return None


async def get_cdi_annual_pct() -> float:
    """Retorna a taxa CDI anual atual em % a.a. (ex: 10.5)."""
    val = await _fetch_brapi_indicator("CDI")
    if val is not None:
        logger.debug("[rf_calc] CDI anual (BRAPI): %.4f%%", val)
        return val
    logger.warning("[rf_calc] usando CDI fallback: %.1f%%", _FALLBACK_CDI_ANNUAL)
    return _FALLBACK_CDI_ANNUAL


async def get_ipca_annual_pct() -> float:
    """Retorna o IPCA anual atual em % a.a. (ex: 5.0)."""
    val = await _fetch_brapi_indicator("IPCA")
    if val is not None:
        logger.debug("[rf_calc] IPCA anual (BRAPI): %.4f%%", val)
        return val
    logger.warning("[rf_calc] usando IPCA fallback: %.1f%%", _FALLBACK_IPCA_ANNUAL)
    return _FALLBACK_IPCA_ANNUAL


# ---------------------------------------------------------------------------
# Cálculo de fator de crescimento
# ---------------------------------------------------------------------------

def _days_since(purchase_date: date) -> int:
    """Dias corridos desde a data de compra até hoje."""
    delta = date.today() - purchase_date
    return max(0, delta.days)


def _growth_factor(annual_pct: float, days: int) -> float:
    """
    Fator de crescimento para `days` dias corridos com taxa anual `annual_pct`.
    Usa capitalização contínua diária: (1 + r)^(d/252)
    onde 252 é o número de dias úteis padrão do mercado brasileiro.
    """
    if annual_pct <= 0 or days <= 0:
        return 1.0
    r = annual_pct / 100.0
    factor = (1 + r) ** (days / 252.0)
    return factor


async def estimate_rf_current_value(
    total_invested: float,
    params: RFParams,
    purchase_date: date,
) -> float:
    """
    Calcula o valor atual estimado de um investimento de RF.

    Args:
        total_invested: Valor investido original em BRL.
        params:         Parâmetros extraídos de `notes`.
        purchase_date:  Data da compra.

    Returns:
        Valor estimado atual em BRL.
    """
    if total_invested <= 0:
        return 0.0

    days = _days_since(purchase_date)
    if days == 0:
        return total_invested

    if params.indexer == "CDI_PCT":
        cdi = await get_cdi_annual_pct()
        effective_rate = cdi * (params.rate / 100.0)
        factor = _growth_factor(effective_rate, days)

    elif params.indexer == "CDI_PLUS":
        cdi = await get_cdi_annual_pct()
        effective_rate = cdi + params.spread
        factor = _growth_factor(effective_rate, days)

    elif params.indexer == "IPCA_PLUS":
        ipca = await get_ipca_annual_pct()
        effective_rate = ipca + params.spread
        factor = _growth_factor(effective_rate, days)

    elif params.indexer == "PREFIXADO":
        factor = _growth_factor(params.rate, days)

    else:
        # UNKNOWN — sem informação, retorna valor investido (sem juros)
        return total_invested

    return round(total_invested * factor, 2)


# ---------------------------------------------------------------------------
# Interface principal: enriquece posições RF com current_value calculado
# ---------------------------------------------------------------------------

async def enrich_rf_positions(
    positions: list[dict],
    transactions_by_ticker: dict[str, list],  # ticker -> [Transaction]
) -> dict[str, float]:
    """
    Para cada posição de RENDA_FIXA, calcula o current_value estimado.

    Args:
        positions: Lista de posições brutas (output de calc_raw_positions).
        transactions_by_ticker: Mapa ticker -> lista de Transaction para extrair
                                 notes e data de compra.

    Returns:
        Mapa ticker -> current_value estimado (BRL).
    """
    result: dict[str, float] = {}

    for pos in positions:
        asset_type = str(pos.get("asset_type", "")).upper()
        if asset_type not in _RF_TYPES:
            continue

        ticker = pos["ticker"]
        total_invested = pos["total_invested"]

        txs = transactions_by_ticker.get(ticker, [])
        if not txs:
            continue

        # Usa a transação de compra mais antiga como data de referência
        buy_txs = [t for t in txs if str(getattr(t, "operation", "")).lower() in ("buy", "compra")]
        if not buy_txs:
            continue

        buy_txs_sorted = sorted(buy_txs, key=lambda t: t.date)
        earliest_tx = buy_txs_sorted[0]
        purchase_date = earliest_tx.date

        # Pega notes da tx mais recente que tenha notes preenchido
        notes = None
        for tx in reversed(buy_txs_sorted):
            if getattr(tx, "notes", None):
                notes = tx.notes
                break

        params = parse_rf_notes(notes)

        if params.indexer == "UNKNOWN":
            logger.debug(
                "[rf_calc] %s sem indexador reconhecido em notes=%r — mantendo total_invested",
                ticker, notes,
            )
            # Sem notes: current_value = total_invested (não estimamos)
            continue

        try:
            current_value = await estimate_rf_current_value(
                total_invested=total_invested,
                params=params,
                purchase_date=purchase_date,
            )
            result[ticker] = current_value
            logger.debug(
                "[rf_calc] %s | invested=%.2f | days=%d | indexer=%s | current=%.2f",
                ticker, total_invested, _days_since(purchase_date),
                params.indexer, current_value,
            )
        except Exception as e:
            logger.warning("[rf_calc] erro ao calcular RF para %s: %s", ticker, e)

    return result
