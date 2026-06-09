import logging
from sqlalchemy.orm import Session
from app.models.position import Position
from app.integrations.brapi import fetch_quotes

logger = logging.getLogger(__name__)

# Tipos de ativo que usam BRAPI (mercado nacional)
NATIONAL_TYPES = {
    "acao nacional",
    "fii",
    "etf nacional",
    "tesouro direto",
}


async def update_quotes_for_portfolio(portfolio_id: int, db: Session) -> int:
    """
    Atualiza current_price e current_value de todas as posicoes
    de uma carteira usando a BRAPI (ativos nacionais).
    Retorna o numero de posicoes atualizadas.
    """
    positions = (
        db.query(Position)
        .filter(Position.portfolio_id == portfolio_id)
        .all()
    )

    national_tickers = [
        p.ticker for p in positions
        if p.asset_type.lower() in NATIONAL_TYPES
    ]

    if not national_tickers:
        return 0

    quotes = await fetch_quotes(national_tickers)
    updated = 0

    for pos in positions:
        price = quotes.get(pos.ticker)
        if price is not None:
            pos.current_price = price
            pos.current_value = price * pos.quantity
            updated += 1

    db.commit()
    logger.info(f"Portfolio {portfolio_id}: {updated}/{len(positions)} posicoes atualizadas")
    return updated


async def update_all_quotes(db: Session) -> None:
    """
    Scheduler job: atualiza cotacoes de TODAS as posicoes ativas.
    Agrupa por ticker para minimizar chamadas a API.
    """
    from app.models.position import Position

    all_positions = db.query(Position).all()

    national = [
        p for p in all_positions
        if p.asset_type.lower() in NATIONAL_TYPES
    ]

    tickers = list({p.ticker for p in national})
    if not tickers:
        return

    quotes = await fetch_quotes(tickers)
    updated = 0

    for pos in national:
        price = quotes.get(pos.ticker)
        if price is not None:
            pos.current_price = price
            pos.current_value = price * pos.quantity
            updated += 1

    db.commit()
    logger.info(f"[scheduler] {updated} posicoes atualizadas")
