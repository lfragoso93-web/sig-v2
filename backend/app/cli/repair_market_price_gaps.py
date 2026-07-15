"""CLI para reparar lacunas históricas dos ativos de mercado da carteira."""
from __future__ import annotations

import argparse
import asyncio
import json

from app.services.market_price_gap_repair_service import repair_market_price_gaps


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("tickers", nargs="*", help="Tickers específicos; usa a lista padrão quando omitido")
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    result = await repair_market_price_gaps(args.tickers or None)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(_main())
