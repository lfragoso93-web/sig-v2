"""
rf_calc_service.py

Calcula o valor atual estimado de posições de Renda Fixa com base nos
juros acumulados desde a data de cada aporte individual.

Indexadores suportados (extraídos do campo `notes` da transação):
  - CDI percentual  : "110% do CDI", "100% CDI", "110%CDI"
  - CDI + spread    : "CDI + 2%", "CDI+1.5%"
  - IPCA + spread   : "IPCA + 5%", "IPCA+4.5% a.a."
  - Prefixado       : "12% a.a.", "12.5%", "prefixado 11%"

Fonte das taxas:
  - CDI e IPCA : endpoint BRAPI /v2/finance (taxa anual atual)
  - Fallback   : estimativas conservadoras fixas quando BRAPI indisponível

Lógica de cálculo:
  Cada transação de compra é tratada individualmente:
    - valor do aporte = quantity * price  (já em BRL no total_cost)
    - dias acumulados = hoje - data da transação
    - fator = (1 + r)^(dias/252)
    - valor_atual_aporte = valor_aporte * fator
  O current_value final é a soma dos valores atuais de cada aporte.
  Vendas parciais reduzem proporcionalmente o saldo pelo ratio FIFO.
"""
from __future__ import annotations

import logging
import re
from datetime import date
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
_FALLBACK_CDI_ANNUAL = 10.5
_FALLBACK_IPCA_ANNUAL = 5.0

BRAPI_BASE = "https://brapi.dev/api"


# ---------------------------------------------------------------------------
# Parser de notas
# ---------------------------------------------------------------------------

class RFParams:
    """Parâmetros extraídos do campo `notes` de uma transação de RF."""

    def __init__(
        self,
        indexer: str,
        rate: float = 0.0,
        spread: float = 0.0,
    ):
        self.indexer = indexer  # CDI_PCT | CDI_PLUS | IPCA_PLUS | PREFIXADO | UNKNOWN
        self.rate = rate        # % CDI (ex: 110.0) ou taxa prefixada a.a.
        self.spread = spread    # spread sobre CDI ou IPCA em % a.a.

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
        return RFParams("CDI_PLUS", spread=float(m.group(1).replace(",", ".")))

    # X% do CDI ou X% CDI
    m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*%\s*(?:do\s+)?CDI", n, re.IGNORECASE)
    if m:
        return RFParams("CDI_PCT", rate=float(m.group(1).replace(",", ".")))

    # CDI puro sem percentual explícito → assume 100%
    if re.search(r"\bCDI\b", n, re.IGNORECASE):
        return RFParams("CDI_PCT", rate=100.0)

    # IPCA + spread: "IPCA + 5%" ou "IPCA+4.5% a.a."
    m = re.search(r"IPCA\s*\+\s*([0-9]+(?:[.,][0-9]+)?)", n, re.IGNORECASE)
    if m:
        return RFParams("IPCA_PLUS", spread=float(m.group(1).replace(",", ".")))

    # IPCA puro
    if re.search(r"\bIPCA\b", n, re.IGNORECASE):
        return RFParams("IPCA_PLUS", spread=0.0)

    # Prefixado: "prefixado 12%" ou "12% a.a." ou "12.5%"
    m = re.search(
        r"(?:prefixado[\s:]*)?([0-9]+(?:[.,][0-9]+)?)\s*%(?:\s*a\.?a\.?)?",
        n, re.IGNORECASE,
    )
    if m:
        return RFParams("PREFIXADO", rate=float(m.group(1).replace(",", ".")))

    return RFParams("UNKNOWN")


# ---------------------------------------------------------------------------
# Busca de taxas via BRAPI
# ---------------------------------------------------------------------------

async def _fetch_brapi_indicator(key: str) -> Optional[float]:
    """Retorna a taxa anual atual (% a.a.) do indicador via BRAPI."""
    cache_key = f"brapi_indicator:{key}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return float(cached)

    try:
        import os
        token = os.getenv("BRAPI_TOKEN", "")
        url = f"{BRAPI_BASE}/v2/finance"
        params: dict = {"key": key}
        if token:
            params["token"] = token

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        for item in data.get("finance", []):
            if str(item.get("key", "")).upper() == key.upper():
                annual = item.get("annual") or item.get("yearly")
                if annual is not None:
                    val = float(str(annual).replace(",", "."))
                    await cache_set(cache_key, val, ttl=_CACHE_TTL)
                    return val
                monthly = item.get("monthly")
                if monthly is not None:
                    m_val = float(str(monthly).replace(",", "."))
                    annual_est = ((1 + m_val / 100) ** 12 - 1) * 100
                    await cache_set(cache_key, annual_est, ttl=_CACHE_TTL)
                    return annual_est
    except Exception as e:
        logger.warning("[rf_calc] BRAPI indicator '%s' falhou: %s", key, e)

    return None


async def get_cdi_annual_pct() -> float:
    val = await _fetch_brapi_indicator("CDI")
    if val is not None:
        return val
    logger.warning("[rf_calc] CDI indisponível — usando fallback %.1f%%", _FALLBACK_CDI_ANNUAL)
    return _FALLBACK_CDI_ANNUAL


async def get_ipca_annual_pct() -> float:
    val = await _fetch_brapi_indicator("IPCA")
    if val is not None:
        return val
    logger.warning("[rf_calc] IPCA indisponível — usando fallback %.1f%%", _FALLBACK_IPCA_ANNUAL)
    return _FALLBACK_IPCA_ANNUAL


# ---------------------------------------------------------------------------
# Fator de crescimento
# ---------------------------------------------------------------------------

def _days_since(purchase_date: date) -> int:
    return max(0, (date.today() - purchase_date).days)


def _growth_factor(annual_pct: float, days: int) -> float:
    """
    Fator de crescimento para `days` dias corridos com taxa anual `annual_pct`.
    Capitalização em dias úteis: (1 + r)^(d/252)
    """
    if annual_pct <= 0 or days <= 0:
        return 1.0
    return (1 + annual_pct / 100.0) ** (days / 252.0)


async def _effective_rate(params: RFParams) -> Optional[float]:
    """Retorna a taxa efetiva anual em % com base no indexador."""
    if params.indexer == "CDI_PCT":
        cdi = await get_cdi_annual_pct()
        return cdi * (params.rate / 100.0)
    elif params.indexer == "CDI_PLUS":
        cdi = await get_cdi_annual_pct()
        return cdi + params.spread
    elif params.indexer == "IPCA_PLUS":
        ipca = await get_ipca_annual_pct()
        return ipca + params.spread
    elif params.indexer == "PREFIXADO":
        return params.rate
    return None


# ---------------------------------------------------------------------------
# Cálculo por aporte individual
# ---------------------------------------------------------------------------

async def _estimate_aporte(
    value: float,
    tx_date: date,
    params: RFParams,
    rate: float,
) -> float:
    """
    Calcula o valor atual estimado de um único aporte.

    Args:
        value    : Valor aportado em BRL (qty * price da tx)
        tx_date  : Data da transação de compra
        params   : Parâmetros do indexador (não usado diretamente aqui,
                   mantido para log)
        rate     : Taxa efetiva anual já calculada pelo chamador

    Returns:
        Valor atual estimado do aporte em BRL.
    """
    days = _days_since(tx_date)
    if days == 0:
        return value
    factor = _growth_factor(rate, days)
    return round(value * factor, 8)  # precisão interna; arredondamento final no caller


# ---------------------------------------------------------------------------
# Interface principal
# ---------------------------------------------------------------------------

async def enrich_rf_positions(
    positions: list[dict],
    transactions_by_ticker: dict[str, list],
) -> dict[str, float]:
    """
    Para cada posição de RENDA_FIXA, calcula o current_value estimado
    somando o valor atualizado de cada aporte individualmente.

    Lógica:
      1. Filtra as transações de compra do ticker.
      2. Ordena por data (mais antiga primeiro).
      3. Para cada compra: calcula valor do aporte = qty * price.
         Aplica fator de crescimento desde a data daquela compra.
      4. Se houver vendas parciais, deduz proporcionalmente o saldo
         pelo custo médio (FIFO simplificado).
      5. current_value = soma dos valores atualizados dos aportes restantes.

    Args:
        positions             : Posições brutas (output de calc_raw_positions).
        transactions_by_ticker: Mapa ticker -> [Transaction].

    Returns:
        Mapa ticker -> current_value estimado (BRL).
    """
    result: dict[str, float] = {}

    for pos in positions:
        asset_type = str(pos.get("asset_type", "")).upper()
        if asset_type not in _RF_TYPES:
            continue

        ticker = pos["ticker"]
        txs = transactions_by_ticker.get(ticker, [])
        if not txs:
            continue

        # Ordena todas as transacoes por data
        txs_sorted = sorted(txs, key=lambda t: (t.date, t.id))

        # Separa compras e vendas
        buy_txs = [
            t for t in txs_sorted
            if str(getattr(t, "operation", "")).lower() in ("buy", "compra")
        ]
        sell_txs = [
            t for t in txs_sorted
            if str(getattr(t, "operation", "")).lower() in ("sell", "venda")
        ]

        if not buy_txs:
            continue

        # Determina o indexador a partir da compra mais recente com notes
        notes = None
        for tx in reversed(buy_txs):
            if getattr(tx, "notes", None):
                notes = tx.notes
                break

        params = parse_rf_notes(notes)

        if params.indexer == "UNKNOWN":
            logger.debug(
                "[rf_calc] %s sem indexador em notes=%r — pulando", ticker, notes
            )
            continue

        # Busca taxa efetiva uma única vez para todos os aportes do ticker
        try:
            rate = await _effective_rate(params)
        except Exception as e:
            logger.warning("[rf_calc] erro ao obter taxa para %s: %s", ticker, e)
            continue

        if rate is None:
            continue

        # Monta lista de aportes: cada compra como (date, valor_brl)
        # valor_brl = qty * price (em BRL, pois RF é sempre BRL)
        aportes: list[tuple[date, float]] = []
        for tx in buy_txs:
            qty = float(tx.quantity or 0)
            price = float(tx.price or 0)
            fees = float(tx.fees or 0)
            valor_aporte = qty * price + fees
            if valor_aporte > 0:
                aportes.append((tx.date, valor_aporte))

        if not aportes:
            continue

        # Desconta vendas proporcionalmente do valor total investido
        # usando racio simples: venda reduz o saldo na proporção do
        # total_invested (sem distorcao de datas, pois RF não tem lote)
        total_aportado = sum(v for _, v in aportes)
        total_vendido = sum(
            float(t.quantity or 0) * float(t.price or 0)
            for t in sell_txs
        )
        # Racio de quanto ainda esta em carteira (0.0 a 1.0)
        if total_aportado > 0:
            ratio_restante = max(0.0, (total_aportado - total_vendido) / total_aportado)
        else:
            ratio_restante = 0.0

        if ratio_restante <= 0:
            continue

        # Calcula valor atualizado de cada aporte e soma
        current_value_total = 0.0
        for tx_date, valor_aporte in aportes:
            valor_restante = valor_aporte * ratio_restante
            try:
                valor_atual = await _estimate_aporte(
                    value=valor_restante,
                    tx_date=tx_date,
                    params=params,
                    rate=rate,
                )
                current_value_total += valor_atual
            except Exception as e:
                logger.warning(
                    "[rf_calc] erro ao estimar aporte %s em %s: %s",
                    ticker, tx_date, e,
                )
                current_value_total += valor_restante  # fallback: sem juros

        result[ticker] = round(current_value_total, 2)
        logger.debug(
            "[rf_calc] %s | %d aportes | ratio=%.4f | indexer=%s | rate=%.4f%% | current=%.2f",
            ticker, len(aportes), ratio_restante,
            params.indexer, rate, result[ticker],
        )

    return result
