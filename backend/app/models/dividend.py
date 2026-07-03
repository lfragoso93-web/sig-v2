"""
Modelo de proventos recebidos por carteira.

Cada registro representa um provento creditado em uma carteira específica,
vinculado opcionalmente a um AssetDividend (evento de provento do ativo).

Índices compostos (Sprint 5B):
  - (portfolio_id, ticker)  — cobre sum_dividends_by_ticker
  - (portfolio_id, status)  — cobre _proventos_total (WHERE status='RECEBIDO')

Campos legados mantidos para compatibilidade com bancos já migrados antes da
normalização do módulo de proventos. Algumas bases ainda possuem `date_ex` e
`date_pagamento` como NOT NULL; por isso esses campos precisam continuar
mapeados e preenchidos junto com `ex_date`/`payment_date`.
"""
import enum

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DividendType(str, enum.Enum):
    DIVIDENDO = "DIVIDENDO"
    JCP = "JCP"
    RENDIMENTO = "RENDIMENTO"
    AMORTIZACAO = "AMORTIZACAO"
    BONIFICACAO = "BONIFICACAO"
    SUBSCRICAO = "SUBSCRICAO"
    OUTROS = "OUTROS"


class DividendStatus(str, enum.Enum):
    RECEBIDO = "RECEBIDO"
    PENDENTE = "PENDENTE"
    CANCELADO = "CANCELADO"
    A_RECEBER = "A_RECEBER"


class Dividend(Base):
    __tablename__ = "dividends"
    __table_args__ = (
        Index("idx_div_portfolio_ticker", "portfolio_id", "ticker"),
        Index("idx_div_portfolio_status", "portfolio_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_dividend_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("asset_dividends.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    portfolio_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[Numeric | None] = mapped_column(Numeric(20, 8), nullable=True)
    total_value: Mapped[Numeric | None] = mapped_column(Numeric(20, 8), nullable=True)
    net_value: Mapped[Numeric | None] = mapped_column(Numeric(20, 8), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(
            DividendStatus,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,
        ),
        nullable=False,
        default="RECEBIDO",
    )

    # ── Campos do backfill atual ───────────────────────────────────────────
    ticker: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    ex_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    payment_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    value_per_unit: Mapped[Numeric | None] = mapped_column(Numeric(20, 8), nullable=True)
    total_received: Mapped[Numeric | None] = mapped_column(Numeric(20, 8), nullable=True)
    dividend_type: Mapped[str | None] = mapped_column(String, nullable=True)

    # ── Campos legados ainda existentes em algumas bases ───────────────────
    date_ex: Mapped[Date | None] = mapped_column(Date, nullable=True)
    date_pagamento: Mapped[Date | None] = mapped_column(Date, nullable=True)

    # ── Relacionamentos ────────────────────────────────────────────────────
    portfolio = relationship("Portfolio", back_populates="dividends")
    asset_dividend = relationship("AssetDividend", back_populates="portfolio_dividends")
