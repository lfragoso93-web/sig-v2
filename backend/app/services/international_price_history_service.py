"""Serviço de carga histórica de cotações para ativos internacionais (Equivalente EOD/COTAHIST internacional)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.services.asset_price_global_backfill_service import (
    run_global_asset_price_backfill,
)

logger = logging.getLogger(__name__)


async def fetch_international_tickers(db: AsyncSession) -> set[str]:
    """Retorna os tickers de ativos internacionais cadastrados no banco de dados."""
    query = select(Asset.ticker).where(
        Asset.asset_type.in_((AssetType.STOCK.value, AssetType.ETF_INTERNACIONAL.value))
    )
    results = (await db.execute(query)).scalars().all()
    return {str(ticker).strip().upper() for ticker in results if ticker}


async def run_international_price_history_backfill(
    db: AsyncSession,
    *,
    tickers: set[str] | None = None,
) -> dict[str, Any]:
    """Executa a coleta e persistência histórica de preços para Stocks e ETFs internacionais."""
    target_tickers = tickers or await fetch_international_tickers(db)

    if not target_tickers:
        logger.info("[intl_price_history] Nenhum ativo internacional encontrado para carga histórica.")
        return {
            "total_tickers": 0,
            "audited": 0,
            "requested": 0,
            "inserted": 0,
            "errors": 0,
            "skipped": 0,
        }

    logger.info(
        "[intl_price_history] Iniciando carga histórica de preços para %d ativos internacionais...",
        len(target_tickers),
    )

    result = await run_global_asset_price_backfill(
        asset_types={AssetType.STOCK.value, AssetType.ETF_INTERNACIONAL.value},
        tickers=target_tickers,
    )

    logger.info(
        "[intl_price_history] Concluído: tickers=%d audited=%d inserted=%d errors=%d",
        len(target_tickers),
        result.get("audited", 0),
        result.get("inserted", 0),
        result.get("errors", 0),
    )

    return {
        "total_tickers": len(target_tickers),
        **result,
    }
