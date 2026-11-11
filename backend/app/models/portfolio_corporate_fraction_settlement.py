"""Modelagem de liquidacoes manuais de fracoes de eventos corporativos por carteira."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from app.core.database import Base


class PortfolioCorporateFractionSettlement(Base):
    """Valor de leilao de fracoes informado/confirmado no escopo de uma carteira."""

    __tablename__ = "portfolio_corporate_fraction_settlements"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "source_event_id",
            name="uq_portfolio_corp_fraction_settlement",
        ),
        CheckConstraint(
            "gross_amount_brl >= 0",
            name="ck_portfolio_corp_fraction_settlement_nonneg",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer,
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_event_id = Column(String(160), nullable=False)
    ticker = Column(String(30), nullable=False)
    gross_amount_brl = Column(Numeric(18, 2), nullable=False)
    settlement_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
