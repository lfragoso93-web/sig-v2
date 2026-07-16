"""CLI do B3 Historical Market Rebuild."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.services.b3_historical_market_rebuild_service import rebuild_b3_historical_market


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importa histórico oficial B3 COTAHIST")
    parser.add_argument("--start-year", type=int, default=None)
    parser.add_argument("--end-year", type=int, default=None)
    parser.add_argument(
        "--details",
        action="store_true",
        help="Inclui o ciclo de vida de todos os ativos no JSON",
    )
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    result = await rebuild_b3_historical_market(args.start_year, args.end_year)
    payload = result.to_dict()
    if not args.details:
        payload.pop("items", None)
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(_main())
