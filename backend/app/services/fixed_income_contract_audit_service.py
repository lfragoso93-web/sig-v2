"""Auditoria DB-only dos metadados necessários ao valuation de Renda Fixa."""
from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import OperationType, Transaction
from app.services.fixed_income_valuation_service import (
    RENDA_FIXA_TYPE,
    _parse_notes,
)


def _operation_value(value: object) -> str:
    return getattr(value, "value", str(value or "")).lower()


async def audit_fixed_income_contracts(db: AsyncSession) -> dict[str, object]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.asset_type == RENDA_FIXA_TYPE)
        .order_by(Transaction.portfolio_id.asc(), Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = list(result.scalars().all())

    purchases = [
        tx for tx in transactions
        if _operation_value(tx.operation) in {OperationType.buy.value, "compra"}
    ]
    redemptions = [
        tx for tx in transactions
        if _operation_value(tx.operation) in {OperationType.sell.value, "venda", "resgate"}
    ]

    complete = 0
    incomplete = 0
    indexers: Counter[str] = Counter()
    missing_tickers: Counter[str] = Counter()

    for tx in purchases:
        indexer, rate, maturity = _parse_notes(getattr(tx, "notes", None))
        # CDI/Selic a 100% podem omitir taxa. Prefixado e inflação+ exigem taxa explícita.
        requires_rate = indexer in {"PREFIXADO", "IPCA_PLUS", "IGPM_PLUS"}
        metadata_ok = bool(indexer) and (not requires_rate or rate > 0)
        if metadata_ok:
            complete += 1
            indexers[indexer] += 1
        else:
            incomplete += 1
            missing_tickers[str(tx.ticker or "RENDA_FIXA").upper()] += 1

    return {
        "transactions": len(transactions),
        "purchases": len(purchases),
        "redemptions": len(redemptions),
        "contracts_complete": complete,
        "contracts_incomplete": incomplete,
        "coverage_pct": round((complete / len(purchases) * 100), 2) if purchases else 100.0,
        "indexers": dict(sorted(indexers.items())),
        "missing_metadata_tickers": dict(missing_tickers.most_common(20)),
    }
