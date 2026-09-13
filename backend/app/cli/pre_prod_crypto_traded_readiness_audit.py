"""Audita readiness das CRIPTO mais transacionadas no livro local, sem writes."""
from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import func, select

from app.cli import pre_prod_crypto_seam_audit, pre_prod_crypto_shallow_history_audit
from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.asset_universe_membership import AssetUniverseMembership
from app.models.transaction import Transaction
from app.services.asset_universe_membership_service import (
    CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY,
    CRYPTO_TOP100_UNIVERSE_KEY,
)
from app.services.crypto_financial_certification_service import (
    FINANCIALLY_CERTIFIED_CRYPTO_STATUSES,
)

DEFAULT_LIMIT = 30
MAX_LIMIT = 50
SYNTHETIC_CERTIFICATION_PROVIDER = "synthetic-certification"
BLOCKING_STATUSES = (
    "HISTORY_START_TRUNCATED",
    "HISTORY_START_COMPLEMENT_GAPPED",
    "HISTORY_START_COMPLEMENT_UNAVAILABLE",
    "HISTORY_START_SHALLOW",
    "HISTORY_START_SHALLOW_UNAVAILABLE",
    "HISTORY_UNAVAILABLE",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audita, sem writes/providers, as CRIPTO com mais compras/vendas "
            "persistidas no livro local."
        )
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    return parser


def _normalize_limit(value: int) -> int:
    return min(MAX_LIMIT, max(1, int(value)))


async def _top_traded_crypto(limit: int) -> list[dict]:
    stmt = (
        select(
            func.upper(Transaction.ticker).label("ticker"),
            func.count(Transaction.id).label("trades"),
            func.sum(func.abs(Transaction.quantity)).label("total_quantity"),
        )
        .join(
            Asset,
            (Asset.asset_type == Transaction.asset_type)
            & (func.upper(Asset.ticker) == func.upper(Transaction.ticker)),
        )
        .where(Transaction.asset_type == AssetType.CRIPTO.value)
        .where(func.lower(func.coalesce(Asset.provider, "")) != SYNTHETIC_CERTIFICATION_PROVIDER)
        .group_by(func.upper(Transaction.ticker))
        .order_by(func.count(Transaction.id).desc(), func.upper(Transaction.ticker).asc())
        .limit(limit)
    )
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(stmt)).all()
    return [
        {
            "ticker": str(row.ticker).upper(),
            "trades": int(row.trades or 0),
            "total_quantity": row.total_quantity,
        }
        for row in rows
    ]


async def _run(*, limit: int = DEFAULT_LIMIT) -> dict:
    normalized_limit = _normalize_limit(limit)
    traded = await _top_traded_crypto(normalized_limit)
    tickers = {item["ticker"] for item in traded}

    async with AsyncSessionLocal() as db:
        asset_rows = (
            await db.execute(
                select(
                    Asset.id,
                    func.upper(Asset.ticker).label("ticker"),
                    Asset.provider_status,
                    func.count(AssetUniverseMembership.id).label("memberships"),
                )
                .outerjoin(
                    AssetUniverseMembership,
                    (AssetUniverseMembership.asset_id == Asset.id)
                    & (
                        AssetUniverseMembership.universe_key.in_(
                            (
                                CRYPTO_TOP100_UNIVERSE_KEY,
                                CRYPTO_SYNTHETIC_CERTIFICATION_UNIVERSE_KEY,
                            )
                        )
                    ),
                )
                .where(Asset.asset_type == AssetType.CRIPTO.value)
                .where(func.upper(Asset.ticker).in_(tickers))
                .group_by(Asset.id, Asset.ticker, Asset.provider_status)
            )
        ).all()
        assets = {
            str(row.ticker).upper(): {
                "asset_id": int(row.id),
                "ticker": str(row.ticker).upper(),
                "provider_status": row.provider_status,
                "memberships": int(row.memberships or 0),
            }
            for row in asset_rows
        }

        duplicate_groups = (
            select(AssetPrice.asset_id, AssetPrice.timestamp)
            .join(Asset, Asset.id == AssetPrice.asset_id)
            .where(Asset.asset_type == AssetType.CRIPTO.value)
            .where(func.upper(Asset.ticker).in_(tickers))
            .group_by(AssetPrice.asset_id, AssetPrice.timestamp)
            .having(func.count(AssetPrice.id) > 1)
            .subquery()
        )
        duplicates = int(
            (
                await db.execute(select(func.count()).select_from(duplicate_groups))
            ).scalar_one()
            or 0
        )

        no_history_rows = (
            await db.execute(
                select(func.upper(Asset.ticker))
                .where(Asset.asset_type == AssetType.CRIPTO.value)
                .where(func.upper(Asset.ticker).in_(tickers))
                .where(
                    ~select(AssetPrice.id)
                    .where(AssetPrice.asset_id == Asset.id)
                    .exists()
                )
            )
        ).scalars().all()

    seam = await pre_prod_crypto_seam_audit._run(tickers=tickers)
    shallow = await pre_prod_crypto_shallow_history_audit._run(tickers=tickers)

    blocking_assets = []
    for item in traded:
        ticker = item["ticker"]
        asset = assets.get(ticker)
        status = str((asset or {}).get("provider_status") or "").strip().upper()
        memberships = int((asset or {}).get("memberships") or 0)
        certified = status in FINANCIALLY_CERTIFIED_CRYPTO_STATUSES
        if not asset or memberships == 0 or not certified or status in BLOCKING_STATUSES:
            blocking_assets.append(
                {
                    **item,
                    "provider_status": (asset or {}).get("provider_status"),
                    "memberships": memberships,
                    "reason": (
                        "asset_not_found"
                        if not asset
                        else "missing_membership"
                        if memberships == 0
                        else "blocking_status"
                        if status in BLOCKING_STATUSES
                        else "not_financially_certified"
                    ),
                }
            )

    ready = (
        bool(traded)
        and not blocking_assets
        and duplicates == 0
        and not no_history_rows
        and int(seam["blocking_gaps"]) == 0
        and int(shallow["shallow_histories"]) == 0
    )

    return {
        "read_only": True,
        "universe_policy": "top_traded_crypto_transactions",
        "limit": normalized_limit,
        "selected": len(traded),
        "crypto_traded_universe_ready": ready,
        "duplicates": duplicates,
        "no_history": sorted(str(ticker).upper() for ticker in no_history_rows),
        "blocking_seams": int(seam["blocking_gaps"]),
        "shallow_histories": int(shallow["shallow_histories"]),
        "blocking_assets": blocking_assets,
        "assets": [
            {
                **item,
                **assets.get(item["ticker"], {}),
            }
            for item in traded
        ],
    }


def main() -> None:
    args = _parser().parse_args()
    print(
        json.dumps(
            asyncio.run(_run(limit=args.limit)),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
