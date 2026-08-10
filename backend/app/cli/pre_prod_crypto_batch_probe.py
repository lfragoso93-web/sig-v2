"""Probe read-only do proximo lote deterministico de CRIPTO sem historico."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.cli.crypto_provider_probe import _probe_one
from app.cli.pre_prod_crypto_batch_selection import (
    DEFAULT_LIMIT,
    _normalize_after_ticker,
    _normalize_limit,
    _run as select_batch,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seleciona CRIPTO sem historico e consulta BRAPI/Yahoo sem persistir dados."
    )
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--after-ticker", default=None)
    return parser


def _coverage_class(brapi: dict, yahoo: dict) -> str:
    brapi_available = bool(brapi.get("ok")) and int(brapi.get("rows") or 0) > 0
    yahoo_available = bool(yahoo.get("ok")) and int(yahoo.get("rows") or 0) > 0
    if brapi_available and yahoo_available:
        return "brapi_and_yahoo"
    if brapi_available:
        return "brapi_only"
    if yahoo_available:
        return "yahoo_only"
    return "unavailable"


async def _run(limit: int, after_ticker: str | None) -> dict:
    selection = await select_batch(limit, after_ticker)
    assets: list[dict] = []
    for selected in selection["assets"]:
        probe = await _probe_one(selected["ticker"])
        coverage_class = _coverage_class(probe["brapi"], probe["yahoo"])
        assets.append(
            {
                **selected,
                "coverage_class": coverage_class,
                "brapi": probe["brapi"],
                "yahoo": probe["yahoo"],
            }
        )

    classes = ("brapi_and_yahoo", "brapi_only", "yahoo_only", "unavailable")
    return {
        "read_only": True,
        "limit": limit,
        "after_ticker": after_ticker,
        "selected": len(assets),
        "by_coverage": {
            coverage_class: sum(
                1 for asset in assets if asset["coverage_class"] == coverage_class
            )
            for coverage_class in classes
        },
        "assets": assets,
    }


def main() -> None:
    args = _parser().parse_args()
    limit = _normalize_limit(args.limit)
    after_ticker = _normalize_after_ticker(args.after_ticker)
    result = asyncio.run(_run(limit, after_ticker))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
