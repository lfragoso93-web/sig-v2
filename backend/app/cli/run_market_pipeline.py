"""
Executa manualmente o pipeline único de mercado por ticker.

Uso dentro do container/backend:

    python -m app.cli.run_market_pipeline --tickers PETR4,BBAS3 --asset-type ACAO
    python -m app.cli.run_market_pipeline --tickers KNRI11 --asset-type FII
    python -m app.cli.run_market_pipeline --tickers PETR4,BBAS3 --asset-type ACAO --concurrency 1

Por padrão o comando executa o pipeline completo:

  - upsert/garantia de Asset;
  - histórico de preços com full=True;
  - logo quando ausente;
  - eventos/proventos globais;
  - materialização para carteiras reais.

Flags permitem desligar etapas específicas para debug.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import asdict
from typing import Iterable

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.services.asset_market_pipeline_service import sync_asset_market_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("market_pipeline_cli")


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _parse_asset_type(value: str) -> AssetType:
    try:
        return AssetType(value.strip().upper())
    except ValueError as exc:
        allowed = ", ".join(t.value for t in AssetType)
        raise argparse.ArgumentTypeError(f"asset-type inválido: {value}. Valores: {allowed}") from exc


async def _load_pairs(tickers: list[str], explicit_type: AssetType | None) -> list[tuple[str, AssetType]]:
    if explicit_type:
        return [(ticker, explicit_type) for ticker in tickers]

    async with AsyncSessionLocal() as db:
        rows = await db.execute(
            select(Asset.ticker, Asset.asset_type)
            .where(Asset.ticker.in_(tickers))
            .order_by(Asset.ticker)
        )
        found = [(str(t).upper(), AssetType(str(at))) for t, at in rows.all() if t and at]

    found_tickers = {ticker for ticker, _ in found}
    missing = sorted(set(tickers) - found_tickers)
    if missing:
        raise SystemExit(
            "Não foi possível inferir o tipo dos tickers não cadastrados: "
            + ", ".join(missing)
            + ". Informe --asset-type."
        )

    return found


async def _run_one(
    ticker: str,
    asset_type: AssetType,
    *,
    full: bool,
    sync_prices: bool,
    sync_logo: bool,
    sync_events: bool,
    materialize: bool,
) -> tuple[str, bool]:
    async with AsyncSessionLocal() as db:
        try:
            result = await sync_asset_market_data(
                db=db,
                ticker=ticker,
                asset_type=asset_type,
                full=full,
                sync_prices=sync_prices,
                sync_logo=sync_logo,
                sync_events=sync_events,
                materialize=materialize,
                commit=True,
            )
            logger.info("OK %s/%s: %s", ticker, asset_type.value, asdict(result))
            return ticker, True
        except Exception as exc:
            logger.exception("FALHA %s/%s: %s", ticker, asset_type.value, exc)
            return ticker, False


async def _run_batches(
    pairs: Iterable[tuple[str, AssetType]],
    *,
    concurrency: int,
    full: bool,
    sync_prices: bool,
    sync_logo: bool,
    sync_events: bool,
    materialize: bool,
) -> int:
    items = list(pairs)
    if not items:
        logger.info("Nenhum ticker para processar.")
        return 0

    logger.info(
        "Executando pipeline de mercado para %s ticker(s), concurrency=%s, full=%s, prices=%s, logo=%s, events=%s, materialize=%s",
        len(items),
        concurrency,
        full,
        sync_prices,
        sync_logo,
        sync_events,
        materialize,
    )

    ok_count = 0
    fail_count = 0
    for i in range(0, len(items), concurrency):
        batch = items[i:i + concurrency]
        results = await asyncio.gather(
            *[
                _run_one(
                    ticker,
                    asset_type,
                    full=full,
                    sync_prices=sync_prices,
                    sync_logo=sync_logo,
                    sync_events=sync_events,
                    materialize=materialize,
                )
                for ticker, asset_type in batch
            ]
        )
        for ticker, ok in results:
            if ok:
                ok_count += 1
            else:
                fail_count += 1

    logger.info("Concluído: ok=%s failed=%s", ok_count, fail_count)
    return 0 if fail_count == 0 else 1


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Executa o pipeline único de mercado por ticker.")
    parser.add_argument("--tickers", required=True, help="Lista CSV de tickers, ex.: PETR4,BBAS3,KNRI11.")
    parser.add_argument(
        "--asset-type",
        type=_parse_asset_type,
        help="Tipo do ativo. Obrigatório para tickers ainda não cadastrados. Ex.: ACAO, FII, ETF_NACIONAL, BDR.",
    )
    parser.add_argument("--concurrency", type=int, default=1, help="Concorrência. Padrão: 1 para facilitar leitura dos logs.")
    parser.add_argument("--incremental", action="store_true", help="Usa full=False para etapa de preços.")
    parser.add_argument("--skip-prices", action="store_true", help="Não sincroniza histórico de preços.")
    parser.add_argument("--skip-logo", action="store_true", help="Não tenta preencher logo.")
    parser.add_argument("--skip-events", action="store_true", help="Não sincroniza eventos/proventos globais.")
    parser.add_argument("--skip-materialize", action="store_true", help="Não materializa eventos nas carteiras.")
    args = parser.parse_args()

    tickers = _parse_csv(args.tickers)
    if not tickers:
        logger.error("Informe ao menos um ticker em --tickers.")
        return 2

    pairs = await _load_pairs(tickers, args.asset_type)
    return await _run_batches(
        pairs,
        concurrency=max(1, args.concurrency),
        full=not args.incremental,
        sync_prices=not args.skip_prices,
        sync_logo=not args.skip_logo,
        sync_events=not args.skip_events,
        materialize=not args.skip_materialize,
    )


def main() -> None:
    try:
        raise SystemExit(asyncio.run(_main()))
    except KeyboardInterrupt:
        logger.warning("Interrompido pelo usuário.")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
