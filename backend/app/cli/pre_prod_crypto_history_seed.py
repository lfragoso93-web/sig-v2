"""Execucao controlada do backfill historico de criptomoedas."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date

from app.core.database import AsyncSessionLocal
from app.models.asset import AssetType
from app.services.asset_price_coverage_service import audit_asset_price_coverage
from app.services.asset_price_global_backfill_service import run_global_asset_price_backfill

MAX_CONCURRENCY = 4
MAX_TICKERS_PER_RUN = 20


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa o backfill historico somente para ativos CRIPTO."
    )
    parser.add_argument("--required-to", type=date.fromisoformat, default=None)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--ticker", action="append", default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _normalize_tickers(values: list[str] | None) -> set[str] | None:
    if values is None:
        return None
    normalized = {str(value).strip().upper() for value in values if str(value).strip()}
    return normalized or None


async def _dry_run(required_to: date | None, tickers: set[str] | None = None) -> dict:
    async with AsyncSessionLocal() as db:
        coverage = await audit_asset_price_coverage(
            db,
            required_to=required_to,
            full_history=True,
        )

    crypto = [
        item
        for item in coverage
        if item.asset_type == AssetType.CRIPTO.value
        and (tickers is None or item.ticker.upper() in tickers)
    ]
    candidates = [item for item in crypto if item.needs_sync and item.asset_id is not None]
    return {
        "dry_run": True,
        "audited": len(crypto),
        "candidates": len(candidates),
        "missing_assets": sum(1 for item in crypto if item.asset_id is None),
        "by_status": {
            status: sum(1 for item in crypto if item.status.value == status)
            for status in sorted({item.status.value for item in crypto})
        },
        "assets": [
            {
                "asset_id": item.asset_id,
                "ticker": item.ticker,
                "status": item.status.value,
                "needs_sync": item.needs_sync,
                "provider": item.provider,
                "provider_symbol": item.provider_symbol,
                "provider_status": item.provider_status,
            }
            for item in crypto
        ],
    }


async def _run(args: argparse.Namespace) -> dict:
    normalized_tickers = _normalize_tickers(args.ticker)
    if args.dry_run:
        return await _dry_run(args.required_to, normalized_tickers)

    if normalized_tickers is None:
        raise SystemExit("execucao real exige ao menos um --ticker")
    if len(normalized_tickers) > MAX_TICKERS_PER_RUN:
        raise SystemExit("execucao real limitada a 20 tickers")

    concurrency = min(MAX_CONCURRENCY, max(1, args.concurrency))
    return await run_global_asset_price_backfill(
        required_to=args.required_to,
        concurrency=concurrency,
        asset_types={AssetType.CRIPTO.value},
        tickers=normalized_tickers,
    )


def main() -> None:
    args = _parser().parse_args()
    result = asyncio.run(_run(args))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
