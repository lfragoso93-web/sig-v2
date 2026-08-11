"""Classifica históricos CRIPTO rasos usando evidência Yahoo max sem writes."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date

from app.cli import pre_prod_crypto_shallow_probe

MAX_TICKERS_PER_CLASSIFY = 20


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classifica shallow histories CRIPTO como recuperáveis ou legítimos sem persistir dados."
    )
    parser.add_argument("--limit", type=int, default=MAX_TICKERS_PER_CLASSIFY)
    parser.add_argument("--after-ticker", default=None)
    parser.add_argument("--required-to", default=None)
    return parser


async def _run(*, limit: int, after_ticker: str | None, required_to: date | None) -> dict:
    if limit < 1 or limit > MAX_TICKERS_PER_CLASSIFY:
        raise SystemExit(f"--limit deve estar entre 1 e {MAX_TICKERS_PER_CLASSIFY}")

    probe = await pre_prod_crypto_shallow_probe._run(
        limit=limit,
        after_ticker=after_ticker,
        required_to=required_to,
    )

    assets = []
    recoverable = 0
    legitimate = 0
    for item in probe["assets"]:
        brapi_first_raw = item.get("first_date")
        yahoo = item.get("yahoo") or {}
        yahoo_first_raw = yahoo.get("first_date")
        brapi_first = date.fromisoformat(brapi_first_raw) if brapi_first_raw else None
        yahoo_first = date.fromisoformat(yahoo_first_raw) if yahoo_first_raw else None

        recovery_class = (
            "recoverable_shallow"
            if yahoo_first is not None and brapi_first is not None and yahoo_first < brapi_first
            else "legitimate_shallow"
        )
        recoverable += int(recovery_class == "recoverable_shallow")
        legitimate += int(recovery_class == "legitimate_shallow")
        assets.append(
            {
                **item,
                "recovery_class": recovery_class,
                "evidence": {
                    "brapi_first_date": brapi_first_raw,
                    "yahoo_first_date": yahoo_first_raw,
                    "yahoo_rows": int(yahoo.get("rows", 0) or 0),
                },
            }
        )

    return {
        "read_only": True,
        "limit": limit,
        "after_ticker": probe.get("after_ticker"),
        "selected": len(assets),
        "by_recovery_class": {
            "recoverable_shallow": recoverable,
            "legitimate_shallow": legitimate,
        },
        "assets": assets,
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
                )
            ),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
