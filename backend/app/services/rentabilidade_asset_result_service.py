"""Resultado financeiro por ativo sem promover retorno simples a TWR."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType, Transaction
from app.services.canonical_positions_service import get_canonical_portfolio_positions
from app.services.realized_pnl_service import get_realized_pnl_by_ticker


def _pct(value: float, base: float) -> float | None:
    if base <= 0:
        return None
    return round(value / base * 100, 4)


async def _transaction_metadata(db: AsyncSession, portfolio_id: int) -> dict[str, dict]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    metadata: dict[str, dict] = defaultdict(lambda: {"invested": 0.0, "asset_type": None})
    for tx in result.scalars().all():
        ticker = str(tx.ticker or "").upper().strip()
        if not ticker:
            continue
        raw_type = getattr(tx.asset_type, "value", tx.asset_type)
        metadata[ticker]["asset_type"] = str(raw_type or "")
        operation = getattr(tx.operation, "value", tx.operation)
        if str(operation).lower() in {OperationType.buy.value, "compra"}:
            fx = float(getattr(tx, "fx_rate", None) or 1)
            metadata[ticker]["invested"] += (
                float(tx.quantity or 0) * float(tx.price or 0) + float(tx.fees or 0)
            ) * fx
    return dict(metadata)


async def get_canonical_asset_results(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> list[dict]:
    """Combina valuation canônico atual e PnL realizado canônico por ticker."""
    groups = await get_canonical_portfolio_positions(db, portfolio_id, user_id)
    realized_by_ticker = await get_realized_pnl_by_ticker(db, portfolio_id)
    metadata = await _transaction_metadata(db, portfolio_id)

    open_tickers: set[str] = set()
    rows: list[dict] = []
    for group in groups:
        for position in group.get("positions", []):
            ticker = str(position.get("ticker") or "").upper().strip()
            if not ticker:
                continue
            open_tickers.add(ticker)
            invested = float(position.get("invested_value") or 0)
            current_raw = position.get("current_value")
            current = float(current_raw) if current_raw is not None else invested
            unrealized = round(current - invested, 2)
            realized = round(float(realized_by_ticker.get(ticker, 0)), 2)
            total = round(unrealized + realized, 2)
            rows.append({
                "ticker": ticker,
                "name": position.get("asset_label") or ticker,
                "asset_type": position.get("asset_type"),
                "quantity": float(position.get("quantity") or 0),
                "avg_price": float(position.get("average_price") or 0),
                "current_price": position.get("current_price"),
                "total_invested": round(invested, 2),
                "current_value": round(current, 2),
                "unrealized_pnl": unrealized,
                "unrealized_pct": _pct(unrealized, invested),
                "realized_pnl": realized,
                "total_pnl": total,
                "total_pnl_pct": _pct(total, invested),
                "is_open": True,
                "result_source": "canonical_positions_and_realized_pnl",
            })

    for ticker, realized in realized_by_ticker.items():
        if ticker in open_tickers or realized == 0:
            continue
        info = metadata.get(ticker, {})
        invested = round(float(info.get("invested") or 0), 2)
        rows.append({
            "ticker": ticker,
            "name": ticker,
            "asset_type": info.get("asset_type"),
            "quantity": 0.0,
            "avg_price": 0.0,
            "current_price": None,
            "total_invested": invested,
            "current_value": 0.0,
            "unrealized_pnl": 0.0,
            "unrealized_pct": None,
            "realized_pnl": round(realized, 2),
            "total_pnl": round(realized, 2),
            "total_pnl_pct": _pct(realized, invested),
            "is_open": False,
            "result_source": "canonical_realized_pnl",
        })

    rows.sort(key=lambda row: (not row["is_open"], -abs(row["total_pnl"])))
    return rows
