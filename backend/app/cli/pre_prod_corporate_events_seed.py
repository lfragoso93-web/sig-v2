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

_SUPPORTED_TYPES = {
    "ACAO",
    "BDR",
    "ETF_NACIONAL",
    "FII",
    "STOCK",
    "ETF_INTERNACIONAL",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio-id", type=int, required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Persiste eventos coletados; sem esta flag o comando faz dry-run.",
    )
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    report = {
        "portfolio_id": args.portfolio_id,
        "dry_run": not args.execute,
        "database_writes_executed": 0,
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
            ticker = str(asset.ticker)
            asset_type = str(asset.asset_type)
            # A dry-run keeps all staged rows in one outer transaction and rolls
            # them back once at the end. Rolling back per asset expires every
            # ORM instance in the session; the next iteration then attempts
            # async lazy I/O while building the report.
            try:
                created = await sync_corporate_events_for_asset(db, asset)
                if args.execute:
                    await db.commit()
                    report["database_writes_executed"] += len(created)
                report["assets_processed"] += 1
                report["events_created"] += len(created)
                report["assets"].append(
                    {
                        "ticker": ticker,
                        "asset_type": asset_type,
                        "created": len(created),
                    }
                )
            except Exception as exc:
                if args.execute:
                    await db.rollback()
                report["errors"].append(
                    {"ticker": ticker, "error": str(exc)}
                )
                break

        if not args.execute:
            await db.rollback()

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
