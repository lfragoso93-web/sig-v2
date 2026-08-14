"""CLI batch para o pipeline único de mercado."""
from __future__ import annotations

import argparse
import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.models.asset import AssetType
from app.services.market_pipeline_batch_service import run_market_pipeline_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("market_pipeline_batch_cli")

DEFAULT_TYPES = {AssetType.ACAO, AssetType.FII, AssetType.ETF_NACIONAL, AssetType.BDR}


def _csv(value: str | None) -> list[str]:
    return [item.strip().upper() for item in (value or "").split(",") if item.strip()]


def _types(value: str | None) -> set[AssetType]:
    if not value:
        return set(DEFAULT_TYPES)
    return {AssetType(item) for item in _csv(value)}


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Executa o pipeline único de mercado em lote.")
    parser.add_argument("--tickers", help="Lista CSV de tickers, opcional.")
    parser.add_argument("--asset-types", help="Lista CSV de tipos. Padrão: ACAO,FII,ETF_NACIONAL,BDR.")
    parser.add_argument("--only-held", action="store_true", help="Processa apenas ativos presentes em transações.")
    parser.add_argument("--limit", type=int, help="Limita a quantidade de ativos elegíveis.")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.0)
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--skip-prices", action="store_true")
    parser.add_argument("--skip-logo", action="store_true")
    args = parser.parse_args()

    async with AsyncSessionLocal() as db:
        result = await run_market_pipeline_batch(
            db,
            asset_types=_types(args.asset_types),
            only_held=args.only_held,
            tickers=_csv(args.tickers),
            limit=args.limit,
            concurrency=max(1, args.concurrency),
            delay=max(0.0, args.delay),
            full=not args.incremental,
            sync_prices=not args.skip_prices,
            sync_logo=not args.skip_logo,
        )

    logger.info("Concluído: ok=%s failed=%s", result.ok, result.failed)
    return 0 if result.failed == 0 else 1


def main() -> None:
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
