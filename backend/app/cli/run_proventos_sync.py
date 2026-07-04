"""
Executa manualmente a sincronização diária de proventos/eventos.

Uso dentro do container/backend:

    python -m app.cli.run_proventos_sync
    python -m app.cli.run_proventos_sync --tickers PETR4,POMO4
    python -m app.cli.run_proventos_sync --asset-types ACAO,FII
    python -m app.cli.run_proventos_sync --concurrency 1

O comando usa o mesmo serviço do cron diário, mas permite acompanhar logs em
primeiro plano durante validações locais.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import asdict

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset
from app.services.dividend_backfill_service import run_backfill, materialize_asset_dividends
from app.services.proventos_daily_sync_service import run_daily_proventos_sync, NATIONAL_EVENT_TYPES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("proventos_sync_cli")


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().upper() for item in value.split(",") if item.strip()]


async def _run_tickers(tickers: list[str], concurrency: int) -> int:
    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(Asset.ticker, Asset.asset_type)
            .where(Asset.ticker.in_(tickers))
            .order_by(Asset.ticker)
        )
        pairs = [(str(t).upper(), str(at)) for t, at in rows.all() if t and at]

    found = {ticker for ticker, _ in pairs}
    missing = sorted(set(tickers) - found)
    if missing:
        logger.warning("Tickers não encontrados em assets: %s", ", ".join(missing))

    if not pairs:
        logger.info("Nenhum ticker elegível para sincronizar.")
        return 0

    logger.info("Sincronizando manualmente %s ticker(s): %s", len(pairs), ", ".join(t for t, _ in pairs))
    synced = 0
    failed = 0

    from app.core.database import AsyncSessionLocal as ItemSession

    for i in range(0, len(pairs), concurrency):
        batch = pairs[i:i + concurrency]

        async def _one(ticker: str, asset_type: str) -> tuple[str, bool]:
            async with ItemSession() as item_db:
                try:
                    await run_backfill(item_db, ticker, asset_type)
                    return ticker, True
                except Exception as exc:
                    logger.exception("Falha ao sincronizar %s/%s: %s", ticker, asset_type, exc)
                    return ticker, False

        results = await asyncio.gather(*[_one(t, at) for t, at in batch])
        for ticker, ok in results:
            if ok:
                synced += 1
                logger.info("OK: %s", ticker)
            else:
                failed += 1
                logger.error("FALHA: %s", ticker)

    async with AsyncSessionLocal() as db:
        materialized = await materialize_asset_dividends(db=db, tickers=tickers, commit=True)
    logger.info("Materialização final: %s vínculo(s) criado(s)/atualizado(s)", materialized)
    logger.info("Concluído: synced=%s failed=%s", synced, failed)
    return 0 if failed == 0 else 1


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Executa sync manual de proventos/eventos BRAPI.")
    parser.add_argument(
        "--tickers",
        help="Lista CSV de tickers para sincronizar, ex.: PETR4,POMO4. Se omitido, roda para todos os ativos nacionais elegíveis.",
    )
    parser.add_argument(
        "--asset-types",
        help="Lista CSV de tipos para sync global, ex.: ACAO,FII. Padrão: ACAO,FII,ETF_NACIONAL,BDR.",
    )
    parser.add_argument("--concurrency", type=int, default=1, help="Concorrência do sync manual. Padrão: 1 para facilitar leitura dos logs.")
    args = parser.parse_args()

    concurrency = max(1, args.concurrency)
    tickers = _parse_csv(args.tickers)
    if tickers:
        return await _run_tickers(tickers, concurrency)

    asset_types = set(_parse_csv(args.asset_types)) if args.asset_types else set(NATIONAL_EVENT_TYPES)
    logger.info("Executando sync global de proventos. asset_types=%s concurrency=%s", sorted(asset_types), concurrency)

    async with AsyncSessionLocal() as db:
        result = await run_daily_proventos_sync(db=db, asset_types=asset_types, concurrency=concurrency)
    logger.info("Resultado: %s", asdict(result))
    return 0 if result.assets_failed == 0 else 1


def main() -> None:
    try:
        raise SystemExit(asyncio.run(_main()))
    except KeyboardInterrupt:
        logger.warning("Interrompido pelo usuário.")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
