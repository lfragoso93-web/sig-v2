"""
price_service.py — Fachada unificada de precos.

Este modulo e o ponto de entrada importado pelo scheduler e por qualquer
codigo novo que precise de cotacoes ou historico de precos.

Re-exporta as funcoes canonicas de:
  - quotes_service     : cotacoes atuais (L1 cache, L2 BRAPI, L3 AV/yfinance)
  - price_history_service : historico diario (L1 BRAPI v2, L2 legado, L3 yfinance)

Uso no scheduler (app/core/scheduler.py):
  from app.services.price_service import update_all_quotes

Uso em endpoints:
  from app.services.price_service import get_current_price, get_price_history

Nunca duplique logica aqui — toda implementacao permanece nos modulos de origem.
"""

# ── Cotacoes atuais ──────────────────────────────────────────────────────────
from app.services.quotes_service import (
    get_prices,
    get_current_price,
    update_all_quotes,
    update_quotes_for_portfolio,
    get_price_for_transaction,
)

# ── Historico de precos ──────────────────────────────────────────────────────
from app.services.price_history_service import (
    persist_daily_prices,
    get_price_at_date,
    get_price_history,
)

__all__ = [
    # cotacoes atuais
    "get_prices",
    "get_current_price",
    "update_all_quotes",
    "update_quotes_for_portfolio",
    "get_price_for_transaction",
    # historico
    "persist_daily_prices",
    "get_price_at_date",
    "get_price_history",
]
