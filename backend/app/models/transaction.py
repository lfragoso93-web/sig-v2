from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column,
    Date,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    desc,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class OperationType(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("idx_txn_portfolio_date", "portfolio_id", desc("date")),
        Index("idx_txn_portfolio_operation", "portfolio_id", "operation"),
        Index("idx_txn_ticker_date", "ticker", desc("date")),
        Index("idx_txn_asset_type", "asset_type"),
        Index("idx_txn_portfolio_date_asc", "portfolio_id", "date", "id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer,
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ticker = Column(String(100), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False)
    operation: Column = Column(
        SAEnum(OperationType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fees = Column(Float, default=0.0)
    date = Column(Date, nullable=False, index=True)
    currency = Column(String(10), default="BRL", nullable=False)
    # Campos da migration 004 — agora expostos no ORM
    fx_rate: Optional[Decimal] = Column(Numeric(18, 8), nullable=True)  # cotacao USD/BRL na data
    price_brl: Optional[Decimal] = Column(Numeric(18, 8), nullable=True)  # preco convertido para BRL
    notes = Column(String(500), nullable=True)

    portfolio = relationship("Portfolio", back_populates="transactions")
