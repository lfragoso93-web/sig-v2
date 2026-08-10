"""Execucao controlada do backfill historico de criptomoedas."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date

from app.models.asset import AssetType
from app.services.asset_price_global_backfill_service import run_global_asset_price_backfill


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa o backfill historico somente para ativos CRIPTO."
    )
    parser.add_argument("--required-to", type=date.fromisoformat, default=None)
    parser.add_argument("--concurrency", type=int, default=4)
    return parser


async def _run(args: argparse.Namespace) -> dict:
    return await run_global_asset_price_backfill(
        required_to=args.required_to,
        concurrency=args.concurrency,
        asset_types={AssetType.CRIPTO.value},
    )


def main() -> None:
    args = _parser().parse_args()
    result = asyncio.run(_run(args))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
