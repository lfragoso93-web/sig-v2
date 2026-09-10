"""Seed pre-prod de eventos corporativos globais por carteira."""
from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset
from app.models.transaction import Transaction
from app.services.corporate_event_service import sync_corporate_events_for_asset

_SUPPORTED_TYPES = {"ACAO", "BDR", "ETF_NACIONAL"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio-id", type=int, required=True)
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    report = {
        "portfolio_id": args.portfolio_id,
        "assets_processed": 0,
        "events_created": 0,
        "errors": [],
        "assets": [],
    }

    async with AsyncSessionLocal() as db:
        tickers = (
            await db.execute(
                select(func.upper(Transaction.ticker))
                .where(Transaction.portfolio_id == args.portfolio_id)
                .distinct()
            )
        ).scalars().all()
        assets = (
            await db.execute(
                select(Asset)
                .where(
                    func.upper(Asset.ticker).in_(tickers),
                    Asset.asset_type.in_(_SUPPORTED_TYPES),
                )
                .order_by(Asset.ticker)
            )
        ).scalars().all()

        for asset in assets:
            try:
                created = await sync_corporate_events_for_asset(db, asset)
                await db.commit()
                report["assets_processed"] += 1
                report["events_created"] += len(created)
                report["assets"].append(
                    {
                        "ticker": asset.ticker,
                        "asset_type": str(asset.asset_type),
                        "created": len(created),
                    }
                )
            except Exception as exc:
                await db.rollback()
                report["errors"].append(
                    {"ticker": asset.ticker, "error": str(exc)}
                )

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
