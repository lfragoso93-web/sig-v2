from datetime import date as DateType, datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    desc,
)
from sqlalchemy.sql import func

from app.core.database import Base


class FxRate(Base):
    """
    Cache persistente de cotacoes de pares de moeda.
    Cada linha representa a cotacao de fechamento (PTAX) de um par cambial em uma data.

    UNIQUE em (pair, rate_date) garante idempotencia em upserts.
    """

    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint("pair", "rate_date", name="uq_fx_rates_pair_date"),
        Index("ix_fx_rates_pair_date", "pair", "rate_date"),
        Index("idx_fx_pair_date_desc", "pair", desc("rate_date")),
    )

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    pair: str = Column(String(10), nullable=False)  # ex: 'USD-BRL'
    rate_date: DateType = Column(Date, nullable=False)  # data da cotacao
    rate: Decimal = Column(Numeric(18, 8), nullable=False)
    created_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
