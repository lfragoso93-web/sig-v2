"""
rf_calc_service.py

Calcula o valor atual estimado de posicoes de Renda Fixa usando o
historico real de taxas armazenado na tabela rate_history (BCB).

Fonte de verdade para indexador/taxa: tabela fixed_income_investments.
Nao existe mais leitura de notes/regex.

Logica por aporte:
  1. Busca dados estruturados em fixed_income_investments (indexer, rate).
  2. Busca taxas diarias do periodo [data_aporte, hoje] em rate_history.
  3. Calcula fator acumulado real: PROD(1 + taxa_diaria_i / 100)
  4. valor_atual_aporte = valor_aporte * fator_acumulado
  current_value = soma dos valores atualizados de todos os aportes.

Fallback: se o banco nao tiver dados do periodo, usa taxa anual corrente
(BRAPI ou constante conservadora).
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

import httpx
from sqlalchemy import text, select

from app.core.cache import cache_get, cache_set
from app.core.database import AsyncSessionLocal
from app.models.fixed_income import FixedIncomeInvestment, IndexerType

log = logging.getLogger(__name__)

_CACHE_TTL = 3600
# Aceita qualquer variante de maiusculas/minusculas
_RF_TYPES = {"renda_fixa", "RENDA_FIXA"}
_FALLBACK_CDI_ANNUAL = 10.5
_FALLBACK_IPCA_ANNUAL = 5.0
BRAPI_BASE = "https://brapi.dev/api"


def _is_rf_type(asset_type: str) -> bool:
    """Retorna True se o asset_type for de Renda Fixa (case-insensitive)."""
    return str(asset_type).upper() == "RENDA_FIXA"


def _op_is_buy(operation) -> bool:
    """
    Retorna True se a operacao for de compra.

    Aceita:
    - OperationType.buy  (enum SQLAlchemy)
    - "buy", "compra"    (string)
    - "OperationType.buy" (repr do enum quando nao desserializado)
    """
    val = str(getattr(operation, "value", operation)).lower()
    return val in ("buy", "compra")


def _op_is_sell(operation) -> bool:
    val = str(getattr(operation, "value", operation)).lower()
    return val in ("sell", "venda")


# ---------------------------------------------------------------------------
# Lookup estruturado em fixed_income_investments
# ---------------------------------------------------------------------------

class RFParams:
    def __init__(self, indexer: str, rate: float = 0.0, spread: float = 0.0):
        self.indexer = indexer
        self.rate = rate
        self.spread = spread

    def __repr__(self) -> str:  # pragma: no cover
        return f"RFParams(indexer={self.indexer!r}, rate={self.rate}, spread={self.spread})"


def _fi_to_params(fi: FixedIncomeInvestment) -> RFParams:
    """Converte modelo fixed_income_investments para RFParams."""
    rate = float(fi.rate or 0)
    idx = fi.indexer

    if idx == IndexerType.CDI:
        # rate armazenado como percentual do CDI (ex: 110 = 110% do CDI)
        return RFParams("CDI_PCT", rate=rate if rate > 0 else 100.0)

    if idx == IndexerType.CDI_PLUS:
        # rate armazenado como spread anual sobre o CDI
        return RFParams("CDI_PLUS", spread=rate)

    if idx == IndexerType.IPCA_PLUS:
        return RFParams("IPCA_PLUS", spread=rate)

    if idx == IndexerType.SELIC:
        return RFParams("CDI_PCT", rate=rate if rate > 0 else 100.0)

    if idx == IndexerType.PREFIXADO:
        return RFParams("PREFIXADO", rate=rate)

    if idx == IndexerType.IGPM_PLUS:
        # Usar IPCA como proxy para IGP-M (fallback conservador)
        return RFParams("IPCA_PLUS", spread=rate)

    return RFParams("UNKNOWN")


async def _get_fi_record(
    portfolio_id: int,
    ticker: str,
) -> Optional[FixedIncomeInvestment]:
    """Busca registro em fixed_income_investments para o ticker na carteira."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FixedIncomeInvestment).where(
                    FixedIncomeInvestment.portfolio_id == portfolio_id,
                    FixedIncomeInvestment.name == ticker,
                )
            )
            return result.scalar_one_or_none()
    except Exception as e:
        log.warning("[rf_calc] Falha ao buscar fi_record %s/%s: %s", ticker, portfolio_id, e)
        return None


# ---------------------------------------------------------------------------
# Fator acumulado real via banco (rate_history)
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
        async with AsyncSessionLocal() as session:
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

    spread_daily = 0.0
    if spread_annual > 0:
        spread_daily = ((1 + spread_annual / 100) ** (1 / 252) - 1) * 100

    factor = 1.0
    for row in rows:
        daily_base = float(row[0])
        effective_daily = daily_base * (pct_of_base / 100.0) + spread_daily
        factor *= (1 + effective_daily / 100)

    ttl = _CACHE_TTL if end_date >= date.today() else 86400
    await cache_set(cache_key, factor, ttl=ttl)
    return factor


# ---------------------------------------------------------------------------
# Fallback BRAPI
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


async def _fallback_factor_annual(annual_pct: float, start_date: date, end_date: date) -> float:
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

async def _estimate_aporte(value: float, start_date: date, params: RFParams) -> float:
    end_date = date.today()
    if start_date >= end_date or value <= 0:
        return value

    factor: Optional[float] = None

    if params.indexer == "CDI_PCT":
        factor = await _accumulated_factor_from_db("CDI", start_date, end_date, pct_of_base=params.rate)
        if factor is None:
            annual = await _get_annual_rate("CDI", _FALLBACK_CDI_ANNUAL)
            factor = await _fallback_factor_annual(annual * (params.rate / 100.0), start_date, end_date)

    elif params.indexer == "CDI_PLUS":
        factor = await _accumulated_factor_from_db("CDI", start_date, end_date, spread_annual=params.spread)
        if factor is None:
            annual = await _get_annual_rate("CDI", _FALLBACK_CDI_ANNUAL)
            factor = await _fallback_factor_annual(annual + params.spread, start_date, end_date)

    elif params.indexer == "IPCA_PLUS":
        factor = await _accumulated_factor_from_db("IPCA", start_date, end_date, spread_annual=params.spread)
        if factor is None:
            annual = await _get_annual_rate("IPCA", _FALLBACK_IPCA_ANNUAL)
            factor = await _fallback_factor_annual(annual + params.spread, start_date, end_date)

    elif params.indexer == "PREFIXADO":
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
    Enriquece posicoes de Renda Fixa com o valor atual estimado.

    Para cada ticker RF:
    - Busca parametros (indexer, rate) diretamente em fixed_income_investments.
    - Calcula o valor atual via fator acumulado real (rate_history) ou fallback.
    - Nao usa regex em notes.
    """
    result: dict[str, float] = {}

    for pos in positions:
        # FIX: comparacao case-insensitive para asset_type
        if not _is_rf_type(pos.get("asset_type", "")):
            continue

        ticker = pos["ticker"]
        portfolio_id = pos.get("portfolio_id")
        txs = transactions_by_ticker.get(ticker, [])
        if not txs:
            continue

        txs_sorted = sorted(txs, key=lambda t: (t.date, t.id))
        # FIX: usa _op_is_buy/_op_is_sell que extrai .value do enum corretamente
        buy_txs  = [t for t in txs_sorted if _op_is_buy(t.operation)]
        sell_txs = [t for t in txs_sorted if _op_is_sell(t.operation)]

        if not buy_txs:
            log.debug("[rf_calc] %s sem compras — pulando", ticker)
            continue

        # --- Busca parametros RF diretamente no banco (sem regex) ---
        params: Optional[RFParams] = None
        if portfolio_id is not None:
            fi_record = await _get_fi_record(portfolio_id, ticker)
            if fi_record is not None:
                params = _fi_to_params(fi_record)

        if params is None or params.indexer == "UNKNOWN":
            log.debug(
                "[rf_calc] %s sem registro em fixed_income_investments (portfolio=%s) — pulando",
                ticker, portfolio_id,
            )
            continue

        # --- Calculo dos aportes ---
        # Para RF: qty=1, price=valor_investido (conforme padrao do modal)
        # Para garantir compatibilidade, usa qty * price + fees em todos os casos
        aportes: list[tuple[date, float]] = []
        total_aportado = 0.0
        for tx in buy_txs:
            qty   = float(tx.quantity or 0)
            price = float(tx.price or 0)
            fees  = float(tx.fees or 0)
            val   = qty * price + fees
            if val > 0:
                aportes.append((tx.date, val))
                total_aportado += val

        if not aportes or total_aportado <= 0:
            continue

        total_vendido = sum(
            float(t.quantity or 0) * float(t.price or 0) for t in sell_txs
        )
        ratio_restante = max(0.0, (total_aportado - total_vendido) / total_aportado)
        if ratio_restante <= 0:
            continue

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
        log.info(
            "[rf_calc] %s | aportes=%d | ratio=%.4f | indexer=%s | current=%.2f",
            ticker, len(aportes), ratio_restante, params.indexer, result[ticker],
        )

    return result
