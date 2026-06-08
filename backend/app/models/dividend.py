from sqlalchemy import Column, Integer, ForeignKey, Numeric, Date, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
from sqlalchemy import Enum as SAEnum


class DividendType(str, enum.Enum):
    DIVIDENDO = "DIVIDENDO"
    JCP = "JCP"
    RENDIMENTO = "RENDIMENTO"
    AMORTIZACAO = "AMORTIZACAO"
    DIVIDENDO_INTERNATIONAL = "DIVIDENDO_INTERNATIONAL"
    CUPOM = "CUPOM"
    OUTROS = "OUTROS"


class Dividend(Base):
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    dividend_type = Column(SAEnum(DividendType), nullable=False)
    ex_date = Column(Date, nullable=False)
    payment_date = Column(Date, nullable=True)
    value_per_unit = Column(Numeric(18, 8), nullable=False)
    quantity_held = Column(Numeric(18, 8), nullable=False)
    total_value = Column(Numeric(18, 4), nullable=False)
    is_automatic = Column(Boolean, default=False, nullable=False)
    brapi_event_id = Column(String(150), nullable=True, unique=True)
    notes = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    portfolio = relationship("Portfolio")
    asset = relationship("Asset")
