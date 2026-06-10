from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class OperationType(str, enum.Enum):
    buy  = "buy"
    sell = "sell"


class Transaction(Base):
    __tablename__ = "transactions"

    id           = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker       = Column(String(20), nullable=False, index=True)
    asset_type   = Column(String(50), nullable=False)
    operation    = Column(SAEnum(OperationType), nullable=False)
    quantity     = Column(Float, nullable=False)
    price        = Column(Float, nullable=False)
    fees         = Column(Float, default=0.0)
    date         = Column(Date, nullable=False, index=True)
    currency     = Column(String(10), default="BRL", nullable=False)
    notes        = Column(String(500), nullable=True)

    portfolio = relationship("Portfolio", back_populates="transactions")
