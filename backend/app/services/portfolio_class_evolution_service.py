"""
Historico patrimonial mensal filtrado por classe de ativo.
Calcula mes a mes somando qty * preco_fechamento para os ativos da classe.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, OperationType
from app.services.price_history_service import get_price_at_date

logger = logging.getLogger(__name__)


def _month_end(year: int, month: int) -> date:
    """Retorna o ultimo dia do mes."""
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    return date(year, month + 1, 1) - timedelta(days=1)


def _parse_asset_type(asset_type: str) -> AssetType | None:
    """Converte string para AssetType enum com fallback None."""
    try:
        return AssetType(asset_type.upper())
    except ValueError:
        logger.warning("[class_evo] asset_type desconhecido: %s", asset_type)
        return None


async def get_monthly_evolution_by_class(
    db: AsyncSession,
    portfolio_id: int,
    months: int = 12,
    asset_type: str = "",
) -> list[dict]:
    """Retorna lista de {date, value, invested} mes a mes para a classe informada."""
    today = date.today()
    since = today - timedelta(days=months * 31)

    # FIX: converter string para enum antes da query para garantir match no PostgreSQL
    parsed_type = _parse_asset_type(asset_type)
    if parsed_type is None:
        logger.warning("[class_evo] asset_type invalido '%s' — retornando vazio", asset_type)
        return []

    result = await db.execute(
        select(Transaction.ticker)
        .join(Asset, Asset.ticker == Transaction.ticker)
        .where(
            Transaction.portfolio_id == portfolio_id,
            Asset.asset_type == parsed_type,  # FIX: enum vs enum (nao string vs enum)
        )
        .distinct()
    )
    tickers = [r.ticker for r in result.all()]

    if not tickers:
        # FIX: fallback — buscar direto nas transacoes sem join em Asset
        # (caso o ticker nao esteja na tabela assets por falha de seed)
        fallback = await db.execute(
            select(Transaction.ticker)
            .where(
                Transaction.portfolio_id == portfolio_id,
                Transaction.asset_type == parsed_type,
            )
            .distinct()
        )
        tickers = [r.ticker for r in fallback.all()]

    if not tickers:
        logger.info(
            "[class_evo] nenhum ticker encontrado para portfolio=%s classe=%s",
            portfolio_id, asset_type,
        )
        return []

    months_to_process: list[tuple[int, int]] = []
    cursor = date(since.year, since.month, 1)
    while cursor <= today:
        months_to_process.append((cursor.year, cursor.month))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    evolution: list[dict] = []

    for year, month in months_to_process:
        target = min(_month_end(year, month), today)

        market_val = Decimal("0")
        invested_val = Decimal("0")

        for ticker in tickers:
            txs_result = await db.execute(
                select(Transaction)
                .where(
                    Transaction.portfolio_id == portfolio_id,
                    Transaction.ticker == ticker,
                    Transaction.date <= target,
                )
                .order_by(Transaction.date.asc(), Transaction.id.asc())
            )
            txs = txs_result.scalars().all()

            qty = Decimal("0")
            cost = Decimal("0")
            for tx in txs:
                q = Decimal(str(tx.quantity))
                p = Decimal(str(tx.price))
                f = Decimal(str(tx.fees or 0))
                if tx.operation == OperationType.buy:
                    cost += q * p + f
                    qty += q
                elif tx.operation == OperationType.sell:
                    sold = min(q, qty)
                    if qty > 0:
                        avg = cost / qty
                        cost -= sold * avg
                    qty -= sold
                    qty = max(qty, Decimal("0"))
                    cost = max(cost, Decimal("0"))

            if qty <= 0:
                continue

            asset_result = await db.execute(select(Asset).where(Asset.ticker == ticker))
            asset = asset_result.scalar_one_or_none()
            a_type = parsed_type if asset is None else asset.asset_type
            close = await get_price_at_date(db, ticker, a_type, target.isoformat())
            if close is None:
                close = float(cost / qty if qty > 0 else Decimal("0"))
                logger.warning(
                    "[class_evo] sem cotacao %s em %s - usando avg_price", ticker, target
                )

            market_val += qty * Decimal(str(close))
            invested_val += cost

        if market_val > 0 or invested_val > 0:
            evolution.append({
                "date": target.strftime("%Y-%m-%d"),
                "value": float(market_val.quantize(Decimal("0.01"))),
                "invested": float(invested_val.quantize(Decimal("0.01"))),
            })

    return evolution
