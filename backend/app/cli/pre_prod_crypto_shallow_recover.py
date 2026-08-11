"""Recupera shallow histories CRIPTO comprovadamente recuperáveis via Yahoo USD/PTAX."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date, timedelta

from app.cli import pre_prod_crypto_shallow_classify
from app.models.asset import AssetType
from app.services import asset_price_gap_sync_service

MAX_TICKERS_PER_RECOVERY = 20
SOURCE = "yfinance_crypto_ptax_brl_max"
SHALLOW_MAX_ROWS = 7
SHALLOW_MAX_AGE_DAYS = 30
VERIFIED_SHALLOW_STATUS = "HISTORY_START_SHALLOW_VERIFIED"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Planeja ou aplica recuperação Yahoo USD/PTAX de shallow histories CRIPTO."
    )
    parser.add_argument("--limit", type=int, default=MAX_TICKERS_PER_RECOVERY)
    parser.add_argument("--after-ticker", default=None)
    parser.add_argument("--required-to", default=None)
    parser.add_argument("--apply", action="store_true")
    return parser


def _continuous_terminal_status(
    complement_rows: list[tuple],
    *,
    brapi_first: date,
) -> str:
    expected_end = brapi_first - timedelta(days=1)
    actual_end = max(timestamp.date() for timestamp, _ in complement_rows)
    if actual_end < expected_end:
        return "HISTORY_START_COMPLEMENT_GAPPED"

    total_rows = len(complement_rows) + 1  # preserva a linha BRAPI existente
    first_date = min(timestamp.date() for timestamp, _ in complement_rows)
    shallow_cutoff = brapi_first - timedelta(days=SHALLOW_MAX_AGE_DAYS)
    if total_rows <= SHALLOW_MAX_ROWS and first_date >= shallow_cutoff:
        return VERIFIED_SHALLOW_STATUS
    return "HISTORY_START_EXHAUSTED"


async def _recover_one(item: dict, *, apply: bool) -> dict:
    ticker = str(item["ticker"]).upper()
    brapi_first = date.fromisoformat(str(item["first_date"]))
    yahoo_symbol = asset_price_gap_sync_service._yahoo_crypto_usd_symbol(ticker)

    result = {
        "asset_id": int(item["asset_id"]),
        "ticker": ticker,
        "recovery_class": item["recovery_class"],
        "brapi_first_date": brapi_first.isoformat(),
        "yahoo_symbol": yahoo_symbol,
        "applied": False,
        "rows_received": 0,
        "rows_inserted": 0,
        "terminal_status": None,
    }
    if item["recovery_class"] != "recoverable_shallow" or not apply:
        return result

    usd_rows = await asset_price_gap_sync_service._fetch_yf_max(yahoo_symbol, AssetType.CRIPTO)
    brl_rows = await asset_price_gap_sync_service._convert_crypto_usd_rows_to_brl(usd_rows)
    complement_rows = [
        (timestamp, close)
        for timestamp, close in brl_rows
        if timestamp.date() < brapi_first
    ]

    result["rows_received"] = len(complement_rows)
    if not complement_rows:
        terminal_status = "HISTORY_START_COMPLEMENT_UNAVAILABLE"
    else:
        terminal_status = _continuous_terminal_status(
            complement_rows,
            brapi_first=brapi_first,
        )

    provider_symbol = str(item.get("provider_symbol") or f"{ticker}-BRL")
    inserted = await asset_price_gap_sync_service._persist_result(
        int(item["asset_id"]),
        complement_rows,
        source=SOURCE,
        provider="brapi",
        provider_symbol=provider_symbol,
        terminal_status=terminal_status,
    )
    result.update(
        {
            "applied": True,
            "rows_inserted": inserted,
            "terminal_status": terminal_status,
        }
    )
    return result


async def _run(
    *,
    limit: int,
    after_ticker: str | None,
    required_to: date | None,
    apply: bool,
) -> dict:
    if limit < 1 or limit > MAX_TICKERS_PER_RECOVERY:
        raise SystemExit(f"--limit deve estar entre 1 e {MAX_TICKERS_PER_RECOVERY}")

    classified = await pre_prod_crypto_shallow_classify._run(
        limit=limit,
        after_ticker=after_ticker,
        required_to=required_to,
    )
    recoverable = [
        item for item in classified["assets"] if item["recovery_class"] == "recoverable_shallow"
    ]

    results = []
    for item in classified["assets"]:
        results.append(await _recover_one(item, apply=apply))

    blocking = sum(
        1
        for item in results
        if item["terminal_status"] in {
            "HISTORY_START_COMPLEMENT_GAPPED",
            "HISTORY_START_COMPLEMENT_UNAVAILABLE",
        }
    )
    return {
        "apply": apply,
        "limit": limit,
        "after_ticker": classified.get("after_ticker"),
        "selected": int(classified["selected"]),
        "recoverable": len(recoverable),
        "applied": sum(1 for item in results if item["applied"]),
        "rows_received": sum(int(item["rows_received"]) for item in results),
        "rows_inserted": sum(int(item["rows_inserted"]) for item in results),
        "blocking_results": blocking,
        "assets": results,
    }


def main() -> None:
    args = _parser().parse_args()
    required_to = date.fromisoformat(args.required_to) if args.required_to else None
    print(
        json.dumps(
            asyncio.run(
                _run(
                    limit=args.limit,
                    after_ticker=args.after_ticker,
                    required_to=required_to,
                    apply=args.apply,
                )
            ),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
