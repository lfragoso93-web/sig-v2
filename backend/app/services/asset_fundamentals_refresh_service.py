"""Serviço de atualização e pré-aquecimento de indicadores fundamentalistas e métricas.

Executado tanto no estágio canônico do bootstrap ('asset_fundamentals')
quanto pelo agendador diário do sistema ('refresh_asset_fundamentals_daily').
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_safety import sanitize_log_value
from app.models.asset import Asset
from app.models.portfolio_position import PortfolioPosition
from app.models.transaction import Transaction
from app.services.asset_enrichment_service import asset_enrichment_service

logger = logging.getLogger(__name__)

# Concorrência máxima para consultas externas de fundamentos/métricas
MAX_CONCURRENT_ENRICHMENT_REQUESTS = 5

_SUPPORTED_FALLBACK_TYPES = (
    "ACAO",
    "FII",
    "STOCK",
    "CRIPTO",
    "TESOURO_DIRETO",
    "RENDA_FIXA",
    "ETF_NACIONAL",
    "ETF_INTERNACIONAL",
)


async def get_distinct_portfolio_and_catalog_assets(
    db: AsyncSession,
    *,
    limit_catalog_fallback: int = 50,
) -> list[tuple[str, str]]:
    """Identifica ativos prioritários para enriquecimento (em carteira, transacionados ou catálogo)."""
    # 1. Ativos com posições abertas ou com transações cadastradas
    pos_subquery = (
        select(PortfolioPosition.asset_id)
        .where(PortfolioPosition.quantity > 0)
        .distinct()
    )
    tx_subquery = select(Transaction.ticker).distinct()

    # Busca ativos vinculados a posições ou transações
    query = (
        select(Asset.ticker, Asset.asset_type)
        .where(
            (Asset.id.in_(pos_subquery))
            | (func.upper(func.trim(Asset.ticker)).in_(tx_subquery))
        )
        .distinct()
    )
    results = (await db.execute(query)).all()
    active_assets = [(str(row[0]).strip().upper(), str(row[1]).strip().upper()) for row in results if row[0]]

    # 2. Se a base não tiver ativos operados ainda (ex: novo bootstrap), carrega principais do catálogo
    if not active_assets:
        catalog_query = (
            select(Asset.ticker, Asset.asset_type)
            .where(Asset.asset_type.in_(_SUPPORTED_FALLBACK_TYPES))
            .limit(limit_catalog_fallback)
        )
        catalog_results = (await db.execute(catalog_query)).all()
        active_assets = [
            (str(row[0]).strip().upper(), str(row[1]).strip().upper())
            for row in catalog_results
            if row[0]
        ]

    # Deduplicação preservando a ordem
    seen = set()
    deduped: list[tuple[str, str]] = []
    for ticker, asset_type in active_assets:
        if ticker not in seen:
            seen.add(ticker)
            deduped.append((ticker, asset_type))

    return deduped


async def run_asset_fundamentals_refresh(
    db: AsyncSession,
    *,
    force_refresh: bool = False,
    limit_catalog: int = 50,
) -> dict[str, int]:
    """Coleta e atualiza indicadores e fundamentos para ativos relevantes."""
    assets = await get_distinct_portfolio_and_catalog_assets(
        db, limit_catalog_fallback=limit_catalog
    )

    stats: dict[str, int] = {
        "total": len(assets),
        "stock": 0,
        "fii": 0,
        "intl": 0,
        "crypto": 0,
        "treasury": 0,
        "errors": 0,
    }

    if not assets:
        logger.info("[asset_fundamentals_refresh] Nenhum ativo encontrado para enriquecimento.")
        return stats

    logger.info(
        "[asset_fundamentals_refresh] Iniciando enriquecimento de %d ativos (force_refresh=%s)...",
        len(assets),
        force_refresh,
    )

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_ENRICHMENT_REQUESTS)

    async def _process_single(ticker: str, asset_type: str) -> None:
        async with semaphore:
            try:
                data = await asset_enrichment_service.get_asset_enrichment(
                    ticker,
                    asset_type,
                    force_refresh=force_refresh,
                )
                if data.get("crypto_indicators"):
                    stats["crypto"] += 1
                elif data.get("treasury_indicators"):
                    stats["treasury"] += 1
                elif data.get("fii_indicators"):
                    stats["fii"] += 1
                elif data.get("international_profile"):
                    stats["intl"] += 1
                elif data.get("stock_fundamentals"):
                    stats["stock"] += 1
            except Exception as exc:
                stats["errors"] += 1
                logger.warning(
                    "[asset_fundamentals_refresh] Erro ao enriquecer %s (%s): %s",
                    sanitize_log_value(ticker),
                    sanitize_log_value(asset_type),
                    sanitize_log_value(exc),
                )

    tasks = [_process_single(ticker, atype) for ticker, atype in assets]
    await asyncio.gather(*tasks, return_exceptions=True)

    logger.info(
        "[asset_fundamentals_refresh] Concluído: total=%d, stock=%d, fii=%d, intl=%d, crypto=%d, treasury=%d, erros=%d",
        stats["total"],
        stats["stock"],
        stats["fii"],
        stats["intl"],
        stats["crypto"],
        stats["treasury"],
        stats["errors"],
    )
    return stats
