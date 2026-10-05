"""
rate_history.py

Modelo SQLAlchemy para a tabela ``rate_history``.
Armazena as series macroeconomicas persistidas usadas pelo SGI:
  - CDI  (Certificado de Deposito Interbancario)
  - SELIC (taxa basica de juros)
  - IPCA (Indice Nacional de Precos ao Consumidor Amplo)
  - IGPM (Indice Geral de Precos - Mercado)

A identidade canonica de uma observacao e ``(indicator, date)``.
"""
from __future__ import annotations

from datetime import date as DateType, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Date, DateTime, Index, Integer, Numeric, String
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
        comment="Indicador: CDI | SELIC | IPCA | IGPM",
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
        comment="Taxa anual em % a.a. (ex: 10.5000)",
    )

    source: str = Column(
        String(32),
        nullable=False,
        default="BCB",
        comment="Fonte da observacao persistida; canonicamente BCB_SGS para benchmarks",
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
