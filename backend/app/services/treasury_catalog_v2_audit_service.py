"""Auditoria das referencias de Tesouro contra o Catalog v2 oficial."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction
from app.services.treasury_catalog_service import resolve_treasury_symbol
from app.services.treasury_catalog_v2_service import fetch_official_treasury_catalog


async def audit_treasury_catalog_v2(db: AsyncSession) -> dict[str, object]:
    official = await fetch_official_treasury_catalog()
    official_symbols = set(official)

    tx_rows = await db.execute(
        select(Transaction.ticker, func.count(Transaction.id))
        .where(Transaction.asset_type == AssetType.TESOURO_DIRETO.value)
        .group_by(Transaction.ticker)
        .order_by(Transaction.ticker.asc())
    )

    valid: list[dict[str, object]] = []
    review: list[dict[str, object]] = []
    grouped: dict[str, int] = defaultdict(int)

    for raw_ticker, count in tx_rows.all():
        ticker = str(raw_ticker or "").strip()
        canonical = await resolve_treasury_symbol(db, ticker)
        item = {
            "ticker": ticker,
            "canonical": canonical,
            "transactions": int(count),
            "official": bool(canonical and canonical in official_symbols),
        }
        if item["official"]:
            valid.append(item)
            grouped[str(canonical)] += int(count)
        else:
            review.append(item)

    asset_rows = await db.execute(
        select(Asset).where(Asset.asset_type == AssetType.TESOURO_DIRETO.value)
    )
    assets = list(asset_rows.scalars().all())
    outside_catalog = [
        {
            "asset_id": int(asset.id),
            "ticker": str(asset.ticker or ""),
            "provider_status": asset.provider_status,
            "provider_last_error": asset.provider_last_error,
        }
        for asset in assets
        if str(asset.ticker or "") not in official_symbols
    ]

    return {
        "official_titles": len(official_symbols),
        "transaction_tickers": len(valid) + len(review),
        "valid_transaction_tickers": len(valid),
        "review_transaction_tickers": len(review),
        "valid_transactions": sum(int(item["transactions"]) for item in valid),
        "review_transactions": sum(int(item["transactions"]) for item in review),
        "canonical_transaction_groups": dict(sorted(grouped.items())),
        "review": review,
        "assets_outside_catalog": outside_catalog,
        "destructive_changes": False,
    }
