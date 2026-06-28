"""
rate_history.py

Modelo SQLAlchemy para a tabela rate_history.
Armazena o historico diario de indicadores macroeconomicos:
  - CDI  (Certificado de Deposito Interbancario)
  - IPCA (Indice Nacional de Precos ao Consumidor Amplo)
  - SELIC (taxa basica de juros)

Cada linha representa a taxa de um indicador em uma data especifica.
As taxas sao armazenadas nas tres granularidades para facilitar
diferentes tipos de calculo sem conversao em runtime.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Date, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class RateHistory(Base):
    __tablename__ = "rate_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    indicator: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="CDI | IPCA | SELIC",
    )
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Data de referencia da taxa",
    )

    # Taxa diaria efetiva em % a.d. (ex: 0.04091 para CDI ~10.5% a.a.)
    rate_daily: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 8),
        nullable=True,
        comment="Taxa diaria efetiva em % a.d.",
    )
    # Taxa mensal em % a.m. (ex: 0.8800 para CDI ~10.5% a.a.)
    rate_monthly: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 8),
        nullable=True,
        comment="Taxa mensal em % a.m.",
    )
    # Taxa anual em % a.a. (ex: 10.5000)
    rate_annual: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 4),
        nullable=True,
        comment="Taxa anual em % a.a.",
    )

    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="BCB",
        comment="BCB | BRAPI | SEED | MANUAL",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
    )

    __table_args__ = (
        Index("uq_rate_history_indicator_date", "indicator", "date", unique=True),
        Index("ix_rate_history_date", "date"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RateHistory indicator={self.indicator!r} "
            f"date={self.date} rate_daily={self.rate_daily}>"
        )
