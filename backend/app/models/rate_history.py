"""
rate_history.py

Modelo SQLAlchemy para a tabela rate_history.
Armazena o historico diario de indicadores macroeconomicos:
  - CDI  (Certificado de Deposito Interbancario)
  - IPCA (Indice Nacional de Precos ao Consumidor Amplo)
  - SELIC (taxa basica de juros)
"""
from __future__ import annotations

from datetime import date as DateType, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String, Date
from sqlalchemy.sql import func

from app.core.database import Base


class RateHistory(Base):
    __tablename__ = "rate_history"

    __table_args__ = (
        Index("uq_rate_history_indicator_date", "indicator", "date", unique=True),
        Index("ix_rate_history_date", "date"),
    )

    id: int = Column(Integer, primary_key=True, autoincrement=True)

    indicator: str = Column(
        String(10),
        nullable=False,
        comment="Indicador: CDI | IPCA | SELIC",
    )
    date: DateType = Column(
        Date,
        nullable=False,
        comment="Data de referencia da taxa",
    )

    # Taxa diaria efetiva em % a.d. (ex: 0.04091 para CDI ~10.5% a.a.)
    rate_daily: Optional[Decimal] = Column(
        Numeric(18, 8),
        nullable=True,
        comment="Taxa diaria efetiva em % a.d.",
    )
    # Taxa mensal em % a.m. (ex: 0.8800)
    rate_monthly: Optional[Decimal] = Column(
        Numeric(18, 8),
        nullable=True,
        comment="Taxa mensal em % a.m.",
    )
    # Taxa anual em % a.a. (ex: 10.5000)
    rate_annual: Optional[Decimal] = Column(
        Numeric(10, 4),
        nullable=True,
        comment="Taxa anual em % a.a.",
    )

    source: str = Column(
        String(20),
        nullable=False,
        default="BCB",
        comment="Fonte: BCB | BRAPI | SEED | MANUAL",
    )
    created_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RateHistory indicator={self.indicator!r} "
            f"date={self.date} rate_daily={self.rate_daily}>"
        )
