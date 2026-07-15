"""Auditoria não destrutiva de aliases e duplicidades do Tesouro Direto."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.transaction import Transaction
from app.services.treasury_catalog_service import resolve_treasury_symbol


async def audit_treasury_canonical_assets(db: AsyncSession) -> dict[str, object]:
    result = await db.execute(
        select(Asset).where(Asset.asset_type == AssetType.TESOURO_DIRETO.value)
    )
    assets = list(result.scalars().all())

    groups: dict[str, list[Asset]] = defaultdict(list)
    unresolved: list[str] = []
    for asset in assets:
        ticker = str(asset.ticker or "").strip()
        canonical = await resolve_treasury_symbol(db, ticker)
        if not canonical:
            unresolved.append(ticker)
            continue
        groups[canonical].append(asset)

    asset_ids = [int(asset.id) for asset in assets]
    price_counts: dict[int, int] = {}
    tx_counts: dict[str, int] = {}
    if asset_ids:
        rows = await db.execute(
            select(AssetPrice.asset_id, func.count(AssetPrice.id))
            .where(AssetPrice.asset_id.in_(asset_ids))
            .group_by(AssetPrice.asset_id)
        )
        price_counts = {int(asset_id): int(count) for asset_id, count in rows.all()}

    tickers = [str(asset.ticker) for asset in assets if asset.ticker]
    if tickers:
        rows = await db.execute(
            select(Transaction.ticker, func.count(Transaction.id))
            .where(
                Transaction.asset_type == AssetType.TESOURO_DIRETO.value,
                Transaction.ticker.in_(tickers),
            )
            .group_by(Transaction.ticker)
        )
        tx_counts = {str(ticker): int(count) for ticker, count in rows.all()}

    duplicates: dict[str, list[dict[str, object]]] = {}
    migration_candidates = 0
    for canonical, grouped in sorted(groups.items()):
        if len(grouped) <= 1:
            continue
        entries = []
        for asset in sorted(grouped, key=lambda item: int(item.id)):
            ticker = str(asset.ticker or "")
            is_canonical = ticker.lower() == canonical.lower()
            if not is_canonical:
                migration_candidates += 1
            entries.append(
                {
                    "asset_id": int(asset.id),
                    "ticker": ticker,
                    "canonical": is_canonical,
                    "price_rows": price_counts.get(int(asset.id), 0),
                    "transaction_rows": tx_counts.get(ticker, 0),
                }
            )
        duplicates[canonical] = entries

    return {
        "assets": len(assets),
        "canonical_groups": len(groups),
        "duplicate_groups": len(duplicates),
        "migration_candidates": migration_candidates,
        "unresolved": sorted(set(unresolved)),
        "duplicates": duplicates,
        "destructive_changes": False,
    }
