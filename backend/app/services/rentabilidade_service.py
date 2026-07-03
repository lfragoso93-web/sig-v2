"""
rentabilidade_service.py

Camada de agregacao sobre dados ja existentes (snapshots + transacoes).
Nao recalcula market_value nem cost_basis — delega ao portfolio_snapshot_service.

Endpoints servidos:
  GET /portfolios/{id}/rentabilidade/kpis
  GET /portfolios/{id}/rentabilidade/ativos
  GET /portfolios/{id}/rentabilidade/classes

Cache Redis (TTL 5 min, prefixo `rent:`):
  Degradacao gracosa se Redis indisponivel.

Histórico de fixes:
  Sprint 5B — retorno_mes_pct corrigido para usar o 1º dia do mês calendário
               em vez de D-30 corridos.
               retorno_dia_pct agora trata fins de semana e feriados buscando
               o snapshot mais recente anterior ao dia corrente (<= D-1),
               evitando retornar 0.0 em dias sem snapshot exato de D-1.
               retorno_12m_pct mantido em D-365 (janela móvel de 12m).
  Sprint 5B — _proventos_total: removido total_received do COALESCE pois a
               coluna existe no modelo mas nunca foi criada via migration.
               Usa apenas total_value (campo principal) com fallback para
               net_value (campo alternativo sempre presente).
  Sprint 5B — get_rentabilidade_por_ativo: eliminado N+1 de get_usd_brl_today
               dentro do loop de ativos. Eliminada segunda query de transactions
               em _get_realized_pnl_by_ticker — reutiliza txs já carregados
               por _load_transactions_by_ticker via _calc_realized_from_txs.
  fix/022   — _proventos_total: payment_date agora existe no banco (migration 022).
               O filtro `since` volta a funcionar corretamente.
               Removida nota de campo inexistente do docstring.
  Sprint 6B — get_rentabilidade_por_ativo e get_rentabilidade_por_classe
               adicionadas ao service (estavam faltando, causando ImportError).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction, OperationType
from app.services.quotes_service import get_prices
from app.services.portfolio_service import (
    calc_raw_positions,
    normalize_type,
    enrich_with_prices,
)
from app.services.fx_service import get_usd_brl_today
from app.core.cache import cache_get, cache_set, cache_delete

logger = logging.getLogger(__name__)

_CACHE_TTL = 300
_PREFIX = "rent"

# Tipos de ativos cotados em USD
_USD_ASSET_TYPES = {"STOCK", "ETF_INTERNACIONAL"}


def _is_rf_type(asset_type: str) -> bool:
    """Retorna True para Renda Fixa (case-insensitive)."""
    return str(asset_type).upper() == "RENDA_FIXA"


def _key(portfolio_id: int, suffix: str) -> str:
    return f"{_PREFIX}:{portfolio_id}:{suffix}"


def _safe_pct(gain: Decimal, base: Decimal) -> float:
    if base and base > 0:
        return round(float(gain / base * 100), 4)
    return 0.0


async def flush_rentabilidade_cache(portfolio_id: int) -> None:
    """
    Invalida as tres chaves de cache de rentabilidade para a carteira.
    Util para chamar apos lancamento de Renda Fixa para garantir
    que o calculo retroativo apareca imediatamente na proxima consulta.
    """
    for suffix in ("kpis", "ativos", "classes"):
        try:
            await cache_delete(_key(portfolio_id, suffix))
        except Exception:
            pass


async def _snapshot_at(
    db: AsyncSession,
    portfolio_id: int,
    target: date,
) -> Optional[PortfolioSnapshot]:
    """Retorna o snapshot mais proximo (<= target)."""
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date <= target,
        )
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _latest_snapshot(
    db: AsyncSession,
    portfolio_id: int,
) -> Optional[PortfolioSnapshot]:
    return await _snapshot_at(db, portfolio_id, date.today())


async def _first_snapshot(
    db: AsyncSession,
    portfolio_id: int,
) -> Optional[PortfolioSnapshot]:
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _snapshot_before_today(
    db: AsyncSession,
    portfolio_id: int,
    snap_today: PortfolioSnapshot,
) -> Optional[PortfolioSnapshot]:
    """
    Sprint 5B FIX — retorno_dia_pct.

    Busca o snapshot imediatamente anterior ao snapshot de hoje (D atual).
    Ao usar snapshot_date < snap_today.snapshot_date (estrito), garantimos que:
      - Fins de semana e feriados são tratados corretamente: se não houver
        snapshot de ontem, usamos o último disponível antes do dia atual.
      - Não confundimos o snapshot de hoje consigo mesmo.
      - Se a carteira só tem um snapshot (o de hoje), retorna None e
        retorno_dia_pct será 0.0 (comportamento correto para carteira nova).
    """
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date < snap_today.snapshot_date,
        )
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _proventos_total(
    db: AsyncSession,
    portfolio_id: int,
    since: Optional[date] = None,
) -> Decimal:
    """
    Soma de proventos recebidos da carteira.

    Usa a tabela `dividends` (Dividend), que tem vinculo direto com portfolio_id
    e os campos corretos: total_value / net_value / status.

    Ordem de preferencia para o valor:
      1. total_value  (campo principal, preenchido pelo backfill moderno)
      2. net_value    (campo alternativo sempre presente no banco)

    Filtro `since`: usa payment_date (criada via migration 022).
    """
    try:
        from app.models.dividend import Dividend, DividendStatus

        value_col = func.coalesce(
            func.sum(
                func.coalesce(Dividend.total_value, Dividend.net_value, Decimal("0"))
            ),
            Decimal("0"),
        )
        q = (
            select(value_col)
            .where(
                Dividend.portfolio_id == portfolio_id,
                Dividend.status == DividendStatus.RECEBIDO,
            )
        )
        if since:
            q = q.where(
                Dividend.payment_date >= since,
            )
        result = await db.execute(q)
        return Decimal(str(result.scalar_one() or 0))
    except Exception as e:
        logger.warning("[rentabilidade] erro ao somar proventos: %s", e)
        return Decimal("0")


def _calc_realized_from_txs(
    txs: list,
) -> dict[str, float]:
    """
    Sprint 5B FIX — elimina N+1 de _get_realized_pnl_by_ticker.

    Calcula o lucro realizado acumulado por ticker a partir de uma lista de
    transacoes ja carregada em memoria (sem nova round-trip ao banco).
    Recebe a lista plana de Transaction objects (ja ordenados por date ASC, id ASC).

    Substitui a funcao async _get_realized_pnl_by_ticker que fazia um SELECT
    separado. Agora e chamada com os dados ja trazidos por _load_transactions_by_ticker,
    evitando a segunda query de transactions por chamada a get_rentabilidade_por_ativo.
    """
    qty_map: dict[str, float] = {}
    cost_map: dict[str, float] = {}  # sempre em BRL
    realized: dict[str, float] = {}

    for tx in txs:
        ticker = tx.ticker.upper()
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)

        asset_type_raw = (
            tx.asset_type.value if hasattr(tx.asset_type, "value") else str(tx.asset_type or "")
        ).upper()
        is_usd = (
            (getattr(tx, "currency", "BRL") or "BRL").upper() == "USD"
            or normalize_type(asset_type_raw) in _USD_ASSET_TYPES
        )

        fx_rate = 1.0
        if is_usd:
            saved = getattr(tx, "fx_rate", None)
            if saved is not None and float(saved or 0) > 0:
                fx_rate = float(saved)

        price_brl = price * fx_rate
        fees_brl = fees * fx_rate

        if ticker not in qty_map:
            qty_map[ticker] = 0.0
            cost_map[ticker] = 0.0
            realized[ticker] = 0.0

        if tx.operation == OperationType.buy:
            qty_map[ticker] += qty
            cost_map[ticker] += qty * price_brl + fees_brl
        elif tx.operation == OperationType.sell:
            sold = min(qty, qty_map[ticker])
            if qty_map[ticker] > 0:
                avg_brl = cost_map[ticker] / qty_map[ticker]
                realized[ticker] += sold * (price_brl - avg_brl)
                cost_map[ticker] -= sold * avg_brl
            qty_map[ticker] = max(0.0, qty_map[ticker] - sold)
            cost_map[ticker] = max(0.0, cost_map[ticker])

    return realized


async def _get_realized_pnl_by_ticker(
    db: AsyncSession,
    portfolio_id: int,
) -> dict[str, float]:
    """
    Mantido para compatibilidade com chamadas externas (ex.: _kpis_from_realtime).
    Internamente delega para _calc_realized_from_txs apos carregar as transacoes.
    """
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = list(result.scalars().all())
    return _calc_realized_from_txs(txs)


async def _load_transactions_by_ticker(
    db: AsyncSession,
    portfolio_id: int,
) -> tuple[dict[str, list], list]:
    """
    Sprint 5B FIX — retorna (by_ticker, flat_list) em vez de apenas by_ticker.

    A flat_list e usada por _calc_realized_from_txs para calcular lucro realizado
    sem nova query, eliminando o N+1 anterior em get_rentabilidade_por_ativo.
    """
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = list(result.scalars().all())
    by_ticker: dict[str, list] = {}
    for tx in txs:
        key = tx.ticker.upper()
        by_ticker.setdefault(key, []).append(tx)
    return by_ticker, txs


async def _calc_invested_up_to(
    db: AsyncSession,
    portfolio_id: int,
    up_to: date,
) -> float:
    """
    Calcula o total investido (custo BRL) acumulado ate uma data.

    Usado pelo fallback realtime para estimar o valor da carteira
    no inicio de um periodo (mes, 12m) quando nao ha snapshots.
    O custo acumulado e um proxy conservador do market_value naquela data:
    subestima os ganhos mas evita retornos inflados por dados ausentes.

    Nao inclui proventos — apenas aportes liquidos (compras - vendas).
    """
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.date <= up_to,
        )
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    txs = result.scalars().all()

    qty_map: dict[str, float] = {}
    cost_map: dict[str, float] = {}

    for tx in txs:
        ticker = tx.ticker.upper()
        qty = float(tx.quantity or 0)
        price = float(tx.price or 0)
        fees = float(tx.fees or 0)

        is_usd = (
            (getattr(tx, "currency", "BRL") or "BRL").upper() == "USD"
            or (tx.asset_type.value if hasattr(tx.asset_type, "value") else str(tx.asset_type or "")).upper()
            in _USD_ASSET_TYPES
        )
        fx_rate = 1.0
        if is_usd:
            saved = getattr(tx, "fx_rate", None)
            if saved is not None and float(saved or 0) > 0:
                fx_rate = float(saved)

        price_brl = price * fx_rate
        fees_brl = fees * fx_rate

        if ticker not in qty_map:
            qty_map[ticker] = 0.0
            cost_map[ticker] = 0.0

        if tx.operation == OperationType.buy:
            qty_map[ticker] += qty
            cost_map[ticker] += qty * price_brl + fees_brl
        elif tx.operation == OperationType.sell:
            sold = min(qty, qty_map[ticker])
            if qty_map[ticker] > 0:
                avg_brl = cost_map[ticker] / qty_map[ticker]
                cost_map[ticker] -= sold * avg_brl
            qty_map[ticker] = max(0.0, qty_map[ticker] - sold)
            cost_map[ticker] = max(0.0, cost_map[ticker])

    return sum(cost_map.values())


async def _kpis_from_realtime(db: AsyncSession, portfolio_id: int) -> dict:
    """
    Fallback: calcula KPIs diretamente das transacoes + cotacoes atuais.
    Usado quando nao existe snapshot para a carteira (ex.: carteira nova
    ou backfill ainda nao executado).

    LIMITACOES deste fallback vs. calculo com snapshots:
    - retorno_dia_pct: sempre 0.0 — impossivel sem snapshot de ontem.
    - retorno_mes_pct: estimado usando custo acumulado ate D-1 do mes
      como proxy do market_value em 01/MM. Usa o 1° dia do mes calendário
      (Sprint 5B FIX), nao D-30 corridos.
    - retorno_12m_pct: estimado usando custo acumulado ate D-365.
    - A chamada a _calc_invested_up_to faz duas queries extras de transacoes;
      e aceitavel para carteiras novas (poucas transacoes) mas seria caro para
      carteiras grandes — neste caso, o backfill de snapshots deve ser priorizado.
    """
    logger.info(
        "[rentabilidade] sem snapshot para portfolio=%s — calculando em tempo real",
        portfolio_id,
    )
    positions_raw = await calc_raw_positions(db, portfolio_id)
    if not positions_raw:
        return {
            "patrimonio_atual": 0.0,
            "custo_total": 0.0,
            "total_aportado": 0.0,
            "ganho_nao_realizado": 0.0,
            "ganho_realizado": 0.0,
            "total_pnl": 0.0,
            "retorno_total_pct": 0.0,
            "retorno_dia_pct": 0.0,
            "retorno_mes_pct": 0.0,
            "retorno_12m_pct": 0.0,
            "retorno_desde_inicio_pct": 0.0,
            "proventos_total": 0.0,
            "proventos_12m": 0.0,
            "snapshot_date": None,
        }

    fx_today = await get_usd_brl_today(db)
    price_items = [
        {"ticker": p["ticker"], "asset_type": p["asset_type"]}
        for p in positions_raw
    ]
    try:
        prices = await get_prices(price_items, db)
    except Exception as e:
        logger.error("[rentabilidade] erro ao buscar precos: %s", e)
        prices = {}
    enriched = enrich_with_prices(positions_raw, prices, fx_today=fx_today)

    total_invested = sum(p["total_invested"] for p in enriched)
    current_value = sum(
        (e["current_value"] if e["current_value"] is not None else e["total_invested"])
        for e in enriched
    )
    unrealized_pnl = current_value - total_invested

    realized_map = await _get_realized_pnl_by_ticker(db, portfolio_id)
    realized_pnl = sum(realized_map.values())
    total_pnl = unrealized_pnl + realized_pnl

    today = date.today()
    proventos_total = float(await _proventos_total(db, portfolio_id))
    proventos_12m = float(await _proventos_total(db, portfolio_id, since=today - timedelta(days=365)))

    retorno_total_pct = (total_pnl / total_invested * 100) if total_invested else 0.0

    retorno_mes_pct = 0.0
    retorno_12m_pct = 0.0
    try:
        primeiro_dia_mes = today.replace(day=1)
        ultimo_dia_mes_anterior = primeiro_dia_mes - timedelta(days=1)
        custo_inicio_mes = await _calc_invested_up_to(db, portfolio_id, ultimo_dia_mes_anterior)
        if custo_inicio_mes > 0:
            retorno_mes_pct = round(
                (current_value - custo_inicio_mes) / custo_inicio_mes * 100, 4
            )
    except Exception as e:
        logger.warning("[rentabilidade] fallback retorno_mes_pct falhou: %s", e)

    try:
        inicio_12m = today - timedelta(days=365)
        custo_inicio_12m = await _calc_invested_up_to(db, portfolio_id, inicio_12m)
        if custo_inicio_12m > 0:
            retorno_12m_pct = round(
                (current_value - custo_inicio_12m) / custo_inicio_12m * 100, 4
            )
    except Exception as e:
        logger.warning("[rentabilidade] fallback retorno_12m_pct falhou: %s", e)

    return {
        "patrimonio_atual": round(current_value, 2),
        "custo_total": round(total_invested, 2),
        "total_aportado": round(total_invested, 2),
        "ganho_nao_realizado": round(unrealized_pnl, 2),
        "ganho_realizado": round(realized_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "retorno_total_pct": round(retorno_total_pct, 4),
        "retorno_dia_pct": 0.0,
        "retorno_mes_pct": retorno_mes_pct,
        "retorno_12m_pct": retorno_12m_pct,
        "retorno_desde_inicio_pct": round(retorno_total_pct, 4),
        "proventos_total": round(proventos_total, 2),
        "proventos_12m": round(proventos_12m, 2),
        "snapshot_date": None,
    }


# ──────────────────────────────────────────────────────────────────────────────
# KPIs
# ──────────────────────────────────────────────────────────────────────────────

def _ret_between(
    snap_end: PortfolioSnapshot,
    snap_start: Optional[PortfolioSnapshot],
) -> float:
    """
    Retorna o percentual de rentabilidade entre dois snapshots.

    Base de cálculo:
      - Sem snap_start: usa invested_total do snap_end como base
        (retorno total sobre capital aportado).
      - Com snap_start: usa market_value do snap_start como base
        (retorno do período sobre patrimônio inicial do período).
        Isso evita distorção por aportes realizados dentro do intervalo,
        aproximando-se do conceito de HPR (Holding Period Return).

    ATENÇÃO: Para janelas longas com muitos aportes, o ideal seria TWR.
    Esta implementação é uma aproximação simples adequada para exibição.
    """
    if snap_start is None:
        base = snap_end.invested_total
        if not base or base == 0:
            return 0.0
        gain = snap_end.unrealized_pnl + snap_end.realized_pnl
        return round(float(gain / base * 100), 4)

    gain_unrealized = snap_end.unrealized_pnl - snap_start.unrealized_pnl
    gain_realized = snap_end.realized_pnl - snap_start.realized_pnl
    total_gain = gain_unrealized + gain_realized

    base = snap_start.market_value
    if not base or base == 0:
        base = snap_start.invested_total
    if not base or base == 0:
        return 0.0

    return round(float(total_gain / base * 100), 4)


async def get_kpis(db: AsyncSession, portfolio_id: int) -> dict:
    cache_key = _key(portfolio_id, "kpis")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    today = date.today()

    snap_today = await _latest_snapshot(db, portfolio_id)

    if snap_today is None:
        payload = await _kpis_from_realtime(db, portfolio_id)
        return payload

    snap_yesterday = await _snapshot_before_today(db, portfolio_id, snap_today)
    snap_mes = await _snapshot_at(db, portfolio_id, today.replace(day=1) - timedelta(days=1))
    snap_12m = await _snapshot_at(db, portfolio_id, today - timedelta(days=365))
    snap_first = await _first_snapshot(db, portfolio_id)

    proventos_total = float(await _proventos_total(db, portfolio_id))
    proventos_12m = float(
        await _proventos_total(db, portfolio_id, since=today - timedelta(days=365))
    )

    payload = {
        "patrimonio_atual":        round(float(snap_today.market_value or 0), 2),
        "custo_total":             round(float(snap_today.cost_basis or 0), 2),
        "total_aportado":          round(float(snap_today.invested_total or 0), 2),
        "ganho_nao_realizado":     round(float(snap_today.unrealized_pnl or 0), 2),
        "ganho_realizado":         round(float(snap_today.realized_pnl or 0), 2),
        "total_pnl":               round(float((snap_today.unrealized_pnl or 0) + (snap_today.realized_pnl or 0)), 2),
        "retorno_total_pct":       _ret_between(snap_today, None),
        "retorno_dia_pct":         _ret_between(snap_today, snap_yesterday),
        "retorno_mes_pct":         _ret_between(snap_today, snap_mes),
        "retorno_12m_pct":         _ret_between(snap_today, snap_12m),
        "retorno_desde_inicio_pct": _ret_between(snap_today, snap_first if snap_first != snap_today else None),
        "proventos_total":         round(proventos_total, 2),
        "proventos_12m":           round(proventos_12m, 2),
        "snapshot_date":           snap_today.snapshot_date.isoformat() if snap_today.snapshot_date else None,
    }

    await cache_set(cache_key, payload, ttl=_CACHE_TTL)
    return payload


# ──────────────────────────────────────────────────────────────────────────────
# Rentabilidade por ativo
# ──────────────────────────────────────────────────────────────────────────────

async def get_rentabilidade_por_ativo(
    db: AsyncSession,
    portfolio_id: int,
) -> list[dict]:
    """
    Retorna lista de dicts com rentabilidade por ativo (posições abertas
    e zeradas com PnL realizado acumulado).

    Campos por item:
      ticker, asset_type, quantity, avg_price, current_price,
      total_invested, current_value, unrealized_pnl, unrealized_pct,
      realized_pnl, total_pnl, total_pct, is_open
    """
    cache_key = _key(portfolio_id, "ativos")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Carrega transações uma vez
    by_ticker, flat_txs = await _load_transactions_by_ticker(db, portfolio_id)
    realized_map = _calc_realized_from_txs(flat_txs)

    # Posições abertas com cotações atuais
    positions_raw = await calc_raw_positions(db, portfolio_id)
    fx_today = await get_usd_brl_today(db)
    price_items = [
        {"ticker": p["ticker"], "asset_type": p["asset_type"]}
        for p in positions_raw
    ]
    try:
        prices = await get_prices(price_items, db)
    except Exception as e:
        logger.error("[rentabilidade] erro ao buscar precos: %s", e)
        prices = {}
    enriched = enrich_with_prices(positions_raw, prices, fx_today=fx_today)

    open_tickers: set[str] = set()
    result: list[dict] = []

    for pos in enriched:
        ticker = str(pos.get("ticker") or pos.get("asset_code") or "").upper()
        if not ticker:
            continue
        open_tickers.add(ticker)

        total_invested = float(pos.get("total_invested") or 0)
        current_value = float(
            pos.get("current_value") if pos.get("current_value") is not None else total_invested
        )
        unrealized_pnl = current_value - total_invested
        unrealized_pct = _safe_pct(
            Decimal(str(unrealized_pnl)), Decimal(str(total_invested))
        ) if total_invested else 0.0
        realized_pnl = realized_map.get(ticker, 0.0)
        total_pnl = unrealized_pnl + realized_pnl
        total_pct = _safe_pct(
            Decimal(str(total_pnl)), Decimal(str(total_invested))
        ) if total_invested else 0.0

        result.append({
            "ticker":          ticker,
            "asset_type":      pos.get("asset_type"),
            "quantity":        float(pos.get("quantity") or 0),
            "avg_price":       float(pos.get("avg_price") or 0),
            "current_price":   float(pos.get("current_price") or 0),
            "total_invested":  round(total_invested, 2),
            "current_value":   round(current_value, 2),
            "unrealized_pnl":  round(unrealized_pnl, 2),
            "unrealized_pct":  unrealized_pct,
            "realized_pnl":    round(realized_pnl, 2),
            "total_pnl":       round(total_pnl, 2),
            "total_pct":       total_pct,
            "total_pnl_pct":   total_pct,
            "is_open":         True,
        })

    # Posições zeradas com PnL realizado
    for ticker, realized_pnl in realized_map.items():
        if ticker in open_tickers or realized_pnl == 0.0:
            continue
        # Custo total de compras para esse ticker
        ticker_txs = by_ticker.get(ticker, [])
        total_invested = sum(
            float(tx.quantity or 0) * float(tx.price or 0)
            for tx in ticker_txs
            if tx.operation == OperationType.buy
        )
        asset_type = None
        if ticker_txs:
            at = ticker_txs[0].asset_type
            asset_type = at.value if hasattr(at, "value") else str(at)

        total_pct = _safe_pct(
            Decimal(str(realized_pnl)), Decimal(str(total_invested))
        ) if total_invested else 0.0

        result.append({
            "ticker":          ticker,
            "asset_type":      asset_type,
            "quantity":        0.0,
            "avg_price":       0.0,
            "current_price":   0.0,
            "total_invested":  round(total_invested, 2),
            "current_value":   0.0,
            "unrealized_pnl":  0.0,
            "unrealized_pct":  0.0,
            "realized_pnl":    round(realized_pnl, 2),
            "total_pnl":       round(realized_pnl, 2),
            "total_pct":       total_pct,
            "total_pnl_pct":   total_pct,
            "is_open":         False,
        })

    result.sort(key=lambda x: (not x["is_open"], -abs(x["total_pnl"])))

    await cache_set(cache_key, result, ttl=_CACHE_TTL)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Rentabilidade por classe
# ──────────────────────────────────────────────────────────────────────────────

async def get_rentabilidade_por_classe(
    db: AsyncSession,
    portfolio_id: int,
) -> list[dict]:
    """
    Agrega rentabilidade por classe de ativo.

    Campos por item:
      asset_type, total_invested, current_value,
      unrealized_pnl, unrealized_pct, realized_pnl,
      total_pnl, total_pct, allocation_pct
    """
    cache_key = _key(portfolio_id, "classes")
    cached = await cache_get(cache_key)
    if cached:
        return cached

    ativos = await get_rentabilidade_por_ativo(db, portfolio_id)

    # Agrega por asset_type
    agg: dict[str, dict] = {}
    for item in ativos:
        at = str(item.get("asset_type") or "OUTROS").upper()
        if at not in agg:
            agg[at] = {
                "asset_type":     at,
                "total_invested": 0.0,
                "current_value":  0.0,
                "unrealized_pnl": 0.0,
                "realized_pnl":   0.0,
                "count":          0,
            }
        agg[at]["total_invested"] += item["total_invested"]
        agg[at]["current_value"]  += item["current_value"]
        agg[at]["unrealized_pnl"] += item["unrealized_pnl"]
        agg[at]["realized_pnl"]   += item["realized_pnl"]
        agg[at]["count"]          += 1

    total_portfolio = sum(v["current_value"] for v in agg.values())

    result: list[dict] = []
    for at, v in agg.items():
        total_pnl = v["unrealized_pnl"] + v["realized_pnl"]
        unrealized_pct = _safe_pct(
            Decimal(str(v["unrealized_pnl"])), Decimal(str(v["total_invested"]))
        ) if v["total_invested"] else 0.0
        total_pct = _safe_pct(
            Decimal(str(total_pnl)), Decimal(str(v["total_invested"]))
        ) if v["total_invested"] else 0.0
        allocation_pct = round(
            v["current_value"] / total_portfolio * 100, 4
        ) if total_portfolio else 0.0

        result.append({
            "asset_type":      at,
            "total_invested":  round(v["total_invested"], 2),
            "current_value":   round(v["current_value"], 2),
            "unrealized_pnl":  round(v["unrealized_pnl"], 2),
            "unrealized_pct":  unrealized_pct,
            "realized_pnl":    round(v["realized_pnl"], 2),
            "total_pnl":       round(total_pnl, 2),
            "total_pct":       total_pct,
            "total_pnl_pct":   total_pct,
            "allocation_pct":  allocation_pct,
            "alocacao_pct":    allocation_pct,
            "count":           v["count"],
        })

    result.sort(key=lambda x: -x["current_value"])

    await cache_set(cache_key, result, ttl=_CACHE_TTL)
    return result
