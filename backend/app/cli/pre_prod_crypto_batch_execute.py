"""Executa lote CRIPTO em duas passagens, com chunks pequenos e gates fail-closed."""
from __future__ import annotations

import argparse
import asyncio
import json
from argparse import Namespace
from datetime import date

from sqlalchemy import select

from app.cli.pre_prod_crypto_batch_selection import (
    DEFAULT_LIMIT,
    _normalize_after_ticker,
    _normalize_limit,
    _run as select_batch,
)
from app.cli.pre_prod_crypto_history_seed import (
    MAX_TICKERS_PER_RUN,
    _run as run_seed,
)
from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType

MAX_OPERATIONAL_BATCH = 50
FIRST_PASS_ALLOWED = {
    "HISTORY_START_EXHAUSTED",
    "HISTORY_START_TRUNCATED",
}
FINAL_ALLOWED = {
    "HISTORY_START_EXHAUSTED",
    "HISTORY_START_COMPLEMENT_UNAVAILABLE",
    "HISTORY_START_COMPLEMENT_GAPPED",
}
BLOCKING_FINAL_STATUSES = {
    "HISTORY_START_COMPLEMENT_UNAVAILABLE",
    "HISTORY_START_COMPLEMENT_GAPPED",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Seleciona CRIPTO sem historico e executa BRAPI primeiro; "
            "Yahoo/PTAX somente para os que ficarem truncados."
        )
    )
    parser.add_argument("--required-to", type=date.fromisoformat, required=True)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--after-ticker", default=None)
    parser.add_argument("--concurrency", type=int, default=1)
    return parser


def _chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


async def _statuses(tickers: list[str]) -> dict[str, str | None]:
    if not tickers:
        return {}
    stmt = (
        select(Asset.ticker, Asset.provider_status)
        .where(Asset.asset_type == AssetType.CRIPTO.value)
        .where(Asset.ticker.in_(tickers))
        .order_by(Asset.ticker.asc())
    )
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(stmt)).all()
    return {row.ticker: row.provider_status for row in rows}


async def _execute_seed(
    tickers: list[str], required_to: date, concurrency: int
) -> list[dict]:
    reports: list[dict] = []
    for chunk in _chunks(tickers, MAX_TICKERS_PER_RUN):
        reports.append(
            await run_seed(
                Namespace(
                    required_to=required_to,
                    concurrency=concurrency,
                    ticker=chunk,
                    dry_run=False,
                )
            )
        )
    return reports


async def _run(args: argparse.Namespace) -> dict:
    requested_limit = _normalize_limit(args.limit)
    limit = min(MAX_OPERATIONAL_BATCH, requested_limit)
    after_ticker = _normalize_after_ticker(args.after_ticker)
    concurrency = max(1, int(args.concurrency))

    selection = await select_batch(limit, after_ticker)
    tickers = [item["ticker"] for item in selection["assets"]]
    if not tickers:
        return {
            "running": False,
            "selected": 0,
            "first_pass": [],
            "second_pass": [],
            "blocking": False,
            "blocking_assets": [],
            "assets": [],
        }

    first_reports = await _execute_seed(tickers, args.required_to, concurrency)
    first_statuses = await _statuses(tickers)
    unexpected_first = {
        ticker: status
        for ticker, status in first_statuses.items()
        if status not in FIRST_PASS_ALLOWED
    }
    if unexpected_first:
        return {
            "running": False,
            "selected": len(tickers),
            "first_pass": first_reports,
            "second_pass": [],
            "blocking": True,
            "blocking_reason": "unexpected_first_pass_status",
            "blocking_assets": unexpected_first,
            "assets": [
                {"ticker": ticker, "provider_status": first_statuses.get(ticker)}
                for ticker in tickers
            ],
        }

    truncated = sorted(
        ticker
        for ticker, status in first_statuses.items()
        if status == "HISTORY_START_TRUNCATED"
    )
    second_reports: list[dict] = []
    processed_second: list[str] = []
    blocking_assets: dict[str, str | None] = {}

    for chunk in _chunks(truncated, MAX_TICKERS_PER_RUN):
        second_reports.extend(await _execute_seed(chunk, args.required_to, concurrency))
        processed_second.extend(chunk)
        current = await _statuses(chunk)
        unexpected = {
            ticker: status
            for ticker, status in current.items()
            if status not in FINAL_ALLOWED
        }
        blocking = {
            ticker: status
            for ticker, status in current.items()
            if status in BLOCKING_FINAL_STATUSES
        }
        blocking_assets.update(unexpected)
        blocking_assets.update(blocking)
        if blocking_assets:
            break

    final_statuses = await _statuses(tickers)
    remaining_truncated = {
        ticker: status
        for ticker, status in final_statuses.items()
        if status == "HISTORY_START_TRUNCATED"
    }
    blocking_assets.update(remaining_truncated)

    return {
        "running": False,
        "selected": len(tickers),
        "limit": limit,
        "after_ticker": after_ticker,
        "first_pass": first_reports,
        "second_pass": second_reports,
        "second_pass_requested": len(truncated),
        "second_pass_processed": len(processed_second),
        "blocking": bool(blocking_assets),
        "blocking_assets": blocking_assets,
        "assets": [
            {"ticker": ticker, "provider_status": final_statuses.get(ticker)}
            for ticker in tickers
        ],
    }


def main() -> None:
    args = _parser().parse_args()
    result = asyncio.run(_run(args))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
