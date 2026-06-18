"""
Orquestrador de cotacoes (Sprint 5).

Responsabilidades:
  - update_quotes_for_portfolio(): atualiza Asset.last_price de todos os ativos
    de uma carteira via Transaction (nao usa PortfolioPosition legada).
  - get_price_for_transaction(): retorna o preco de um ativo em uma data
    especifica. Usado pelo transaction_service ao registrar operacoes retroativas.

O que NAO faz:
  - update_all_quotes() foi removido — usar quotes_service.update_all_quotes()
    que e a versao canonica com cache L1/L2/L3.
  - Nao importa PortfolioPosition (model legado).
  - Nao define seus proprios sets de tipos — usa asset_types.py.
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import AssetType
from app.models.transaction import Transaction
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

    Usa Transaction como fonte de verdade (substitui PortfolioPosition legada).
    Fluxo:
      1. Busca tickers e asset_types distintos das transacoes da carteira.
      2. Monta lista de {ticker, asset_type} para get_prices().
      3. get_prices() consulta L1/L2 do cache e so vai a API para o que expirou.
      4. Persiste last_price em Asset via _db_set() interno do quotes_service.
      5. Commit unico ao final.
    """
    result = await db.execute(
        select(Transaction.ticker, Transaction.asset_type)
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
    )
    rows = result.all()

    if not rows:
        return 0

    positions_payload = [
        {"ticker": r.ticker, "asset_type": r.asset_type}
        for r in rows
        if r.ticker
    ]

    quotes = await get_prices(positions_payload, db=db)
    await db.commit()

    updated = sum(1 for r in rows if r.ticker in quotes)
    logger.info(
        f"[quote_service] Portfolio {portfolio_id}: "
        f"{updated}/{len(rows)} ativos com cotacao atualizada"
    )
    return updated


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
