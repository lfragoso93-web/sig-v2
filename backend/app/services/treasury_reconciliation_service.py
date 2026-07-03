"""
Reconciliação de lançamentos existentes de Tesouro Direto.

Objetivo:
- pegar transações antigas cadastradas com nome livre, ex.:
  "TESOURO RENDA+ APOSENTADORIA EXTRA 2060";
- resolver para o symbol canônico usado pelo SGI/BRAPI, ex.:
  "tesouro-renda-mais-2060";
- atualizar transactions.ticker;
- garantir que o Asset canônico exista em assets.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction
from app.services.treasury_catalog_service import resolve_treasury_symbol

logger = logging.getLogger(__name__)

_TREASURY_TYPE = AssetType.TESOURO_DIRETO.value


@dataclass
class TreasuryReconciliationResult:
    scanned: int = 0
    updated_transactions: int = 0
    created_assets: int = 0
    unresolved: int = 0
    errors: int = 0


def _is_treasury(asset_type: Optional[str]) -> bool:
    raw = str(asset_type or "").strip().lower()
    return raw in {"tesouro_direto", "tesouro direto", "treasury"}


async def _ensure_asset(db: AsyncSession, symbol: str, fallback_name: str | None = None) -> bool:
    existing = await db.execute(
        select(Asset).where(
            Asset.ticker == symbol,
            Asset.asset_type == _TREASURY_TYPE,
        )
    )
    if existing.scalar_one_or_none():
        return False

    db.add(
        Asset(
            ticker=symbol,
            name=fallback_name or symbol,
            asset_type=_TREASURY_TYPE,
            currency="BRL",
            sector="Tesouro Direto | fonte=reconciliacao",
        )
    )
    return True


async def reconcile_treasury_transactions(
    db: AsyncSession,
    commit: bool = True,
) -> TreasuryReconciliationResult:
    """Normaliza tickers de transações existentes de Tesouro Direto."""
    result = TreasuryReconciliationResult()

    query = await db.execute(select(Transaction).order_by(Transaction.id.asc()))
    transactions = [tx for tx in query.scalars().all() if _is_treasury(tx.asset_type)]

    for tx in transactions:
        result.scanned += 1
        raw_ticker = str(tx.ticker or "").strip()
        if not raw_ticker:
            result.unresolved += 1
            continue

        try:
            symbol = await resolve_treasury_symbol(db, raw_ticker)
            if not symbol:
                result.unresolved += 1
                continue

            if await _ensure_asset(db, symbol, fallback_name=raw_ticker):
                result.created_assets += 1

            if raw_ticker != symbol:
                logger.info(
                    "[treasury_reconcile] tx=%s: %r -> %s",
                    tx.id,
                    raw_ticker,
                    symbol,
                )
                tx.ticker = symbol
                tx.asset_type = _TREASURY_TYPE
                result.updated_transactions += 1
        except Exception as exc:
            logger.warning(
                "[treasury_reconcile] falha ao reconciliar tx=%s ticker=%r: %s",
                tx.id,
                raw_ticker,
                exc,
            )
            result.errors += 1

    if commit:
        await db.commit()

    logger.info(
        "[treasury_reconcile] concluído: %d lidos, %d transações atualizadas, %d assets criados, %d sem match, %d erros",
        result.scanned,
        result.updated_transactions,
        result.created_assets,
        result.unresolved,
        result.errors,
    )
    return result
