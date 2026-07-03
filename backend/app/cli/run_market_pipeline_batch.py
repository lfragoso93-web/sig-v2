"""CLI batch para o pipeline único de mercado."""
from __future__ import annotations

import argparse
import asyncio
import logging
import re
from dataclasses import asdict

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction
from app.services.asset_market_pipeline_service import sync_asset_market_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("market_pipeline_batch_cli")

DEFAULT_TYPES = {AssetType.ACAO, AssetType.FII, AssetType.ETF_NACIONAL, AssetType.BDR}
_MAIN_TICKER_RE = re.compile(r"^[A-Z0-9]{4,6}(3|4|5|6|11|31|32|33|34|35)$")


def _csv(value: str | None) -> list[str]:
    return [item.strip().upper() for item in (value or "").split(",") if item.strip()]


def _types(value: str | None) -> set[AssetType]:
    if not value:
        return set(DEFAULT_TYPES)
    parsed: set[AssetType] = set()
    for item in _csv(value):
        parsed.add(AssetType(item))
    return parsed


def _db_type(value) -> AssetType | None:
    raw = str(value or "").replace("AssetType.", "").upper()
    try:
        return AssetType(raw)
    except ValueError:
        return None


def _eligible_ticker(ticker: str) -> bool:
    t = ticker.upper()
    if t.endswith("F") or t[-1:] in {"B", "D", "R"} or t[-2:] in {"97", "98", "99"}:
        return False
    return bool(_MAIN_TICKER_RE.match(t))


async def _load_pairs(tickers: list[str], asset_types: set[AssetType], only_held: bool) -> list[tuple[str, AssetType]]:
    wanted = sorted(at.value for at in asset_types)
    async with AsyncSessionLocal() as db:
        if tickers:
            stmt = select(Asset.ticker, Asset.asset_type).where(Asset.ticker.in_(tickers), Asset.asset_type.in_(wanted))
        elif only_held:
            stmt = select(Transaction.ticker, Transaction.asset_type).where(Transaction.asset_type.in_(wanted)).distinct()
        else:
            stmt = select(Asset.ticker, Asset.asset_type).where(Asset.asset_type.in_(wanted))
        rows = await db.execute(stmt)

    pairs: list[tuple[str, AssetType]] = []
    for ticker, raw_type in rows.all():
        at = _db_type(raw_type)
        if ticker and at:
            pairs.append((str(ticker).upper(), at))

    return sorted(set(pairs), key=lambda item: (item[1].value, item[0]))


async def _run_one(ticker: str, asset_type: AssetType, args: argparse.Namespace) -> tuple[str, bool]:
    async with AsyncSessionLocal() as db:
        try:
            result = await sync_asset_market_data(
                db=db,
                ticker=ticker,
                asset_type=asset_type,
                full=not args.incremental,
                sync_prices=not args.skip_prices,
                sync_logo=not args.skip_logo,
                sync_events=not args.skip_events,
                materialize=not args.skip_materialize,
                commit=True,
            )
            logger.info("OK %s/%s: %s", ticker, asset_type.value, asdict(result))
            return ticker, True
        except Exception as exc:
            logger.exception("FALHA %s/%s: %s", ticker, asset_type.value, exc)
            return ticker, False


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
    parser.add_argument("--skip-events", action="store_true")
    parser.add_argument("--skip-materialize", action="store_true")
    args = parser.parse_args()

    asset_types = _types(args.asset_types)
    raw_pairs = await _load_pairs(_csv(args.tickers), asset_types, args.only_held)
    pairs = [(ticker, at) for ticker, at in raw_pairs if _eligible_ticker(ticker)]
    skipped = len(raw_pairs) - len(pairs)
    if args.limit and args.limit > 0:
        pairs = pairs[: args.limit]

    logger.info(
        "Escopo batch: candidatos=%s elegíveis=%s ignorados=%s asset_types=%s only_held=%s limit=%s",
        len(raw_pairs), len(pairs), skipped, sorted(at.value for at in asset_types), args.only_held, args.limit,
    )

    ok = 0
    failed = 0
    concurrency = max(1, args.concurrency)
    for i in range(0, len(pairs), concurrency):
        batch = pairs[i:i + concurrency]
        results = await asyncio.gather(*[_run_one(ticker, at, args) for ticker, at in batch])
        for _, success in results:
            ok += 1 if success else 0
            failed += 0 if success else 1
        logger.info("Progresso: %s/%s | ok=%s failed=%s", min(i + concurrency, len(pairs)), len(pairs), ok, failed)
        if args.delay > 0 and i + concurrency < len(pairs):
            await asyncio.sleep(args.delay)

    logger.info("Concluído: ok=%s failed=%s", ok, failed)
    return 0 if failed == 0 else 1


def main() -> None:
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
