"""
Orquestrador de cotações (Sprint 5).

Responsabilidades:
  - update_quotes_for_portfolio(): atualiza Asset.last_price de todos os ativos
    de uma carteira sem tocar na tabela `positions` (legada).
  - update_all_quotes(): versao para o scheduler — atualiza todos os ativos
    distintos cadastrados na tabela `assets`.
  - get_price_for_transaction(): retorna o preco de um ativo em uma data
    específica, consultando o banco primeiro (L1/L2) e a API só se necessario.
    Usado pelo transaction_service ao registrar operacoes retroativas.

O que NAO faz mais:
  - Nao grava current_price / current_value em `positions` (tabela legada).
  - Nao importa fetch_international_quotes / yfinance_client diretamente.
  - Nao define seus proprios sets de tipos — usa asset_types.py.
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import ALL_TYPES
from app.models.asset import Asset, AssetType
from app.models.portfolio_position import PortfolioPosition
from app.services.quotes_service import get_prices
from app.services.price_history_service import get_price_at_date

logger = logging.getLogger(__name__)


async def update_quotes_for_portfolio(
    portfolio_id: int,
    db: AsyncSession,
) -> int:
    """
    Atualiza Asset.last_price para todos os ativos de uma carteira.
    Retorna o numero de ativos atualizados.

    Fluxo:
      1. Busca PortfolioPositions da carteira.
      2. Monta lista de {ticker, asset_type} para get_prices().
      3. get_prices() consulta L1/L2 do cache e só vai à API para o que expirou.
      4. Persiste last_price em Asset via _db_set() interno do quotes_service.
      5. Commit unico ao final.
    """
    result = await db.execute(
        select(PortfolioPosition)
        .where(PortfolioPosition.portfolio_id == portfolio_id)
    )
    pp_list = result.scalars().all()

    if not pp_list:
        return 0

    positions_payload = [
        {"ticker": pp.asset.ticker, "asset_type": pp.asset.asset_type.value}
        for pp in pp_list
        if pp.asset is not None
    ]

    quotes = await get_prices(positions_payload, db=db)
    await db.commit()

    updated = sum(1 for pp in pp_list if pp.asset and pp.asset.ticker in quotes)
    logger.info(
        f"[quote_service] Portfolio {portfolio_id}: "
        f"{updated}/{len(pp_list)} ativos com cotação atualizada"
    )
    return updated


async def update_all_quotes(db: AsyncSession) -> None:
    """
    Scheduler: atualiza last_price de todos os ativos distintos em `assets`.
    Só processa tipos reconhecidos em ALL_TYPES.
    Usa get_prices() com db para aproveitar cache L1 e evitar requests redundantes.
    """
    result = await db.execute(
        select(Asset).where(Asset.asset_type.in_(list(ALL_TYPES)))
    )
    assets = result.scalars().all()

    if not assets:
        return

    positions_payload = [
        {"ticker": a.ticker, "asset_type": a.asset_type.value}
        for a in assets
    ]

    quotes = await get_prices(positions_payload, db=db)
    await db.commit()

    updated = sum(1 for a in assets if a.ticker in quotes)
    logger.info(
        f"[quote_service] scheduler: {updated}/{len(assets)} ativos atualizados"
    )


async def get_price_for_transaction(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    date_str: str,
) -> float | None:
    """
    Retorna o preco de fechamento de um ativo em uma data especifica (YYYY-MM-DD).
    Usado pelo transaction_service ao registrar operacoes retroativas.

    Fluxo (via get_price_at_date do price_history_service):
      1. Consulta asset_prices no banco — janela de 5 dias antes de date_str.
      2. Se nao encontrar, dispara persist_daily_prices() — BRAPI Pro ou yfinance.
      3. Retorna o fechamento mais recente disponivel na janela.
      4. Retorna None se nenhuma fonte tiver o dado (sem lancar excecao).
    """
    try:
        return await get_price_at_date(db, ticker, asset_type, date_str)
    except Exception as e:
        logger.warning(
            f"[quote_service] get_price_for_transaction falhou para "
            f"{ticker} em {date_str}: {e}"
        )
        return None
