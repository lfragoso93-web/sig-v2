from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class DividendStatus(str, enum.Enum):
    RECEBIDO = "RECEBIDO"
    A_RECEBER = "A_RECEBER"


class DividendType(str, enum.Enum):
    DIVIDENDO = "DIVIDENDO"
    JCP = "JCP"
    RENDIMENTO = "RENDIMENTO"
    AMORTIZACAO = "AMORTIZACAO"
    BONIFICACAO = "BONIFICACAO"
    OUTROS = "OUTROS"


class Dividend(Base):
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    dividend_type = Column(SAEnum(DividendType), nullable=False, default=DividendType.DIVIDENDO)
    status = Column(SAEnum(DividendStatus), nullable=False, default=DividendStatus.A_RECEBER)
    ex_date = Column(Date, nullable=False)
    payment_date = Column(Date, nullable=True)
    quantity = Column(Numeric(18, 8), nullable=False)
    value_per_unit = Column(Numeric(18, 8), nullable=False)
    total_value = Column(Numeric(18, 8), nullable=False)
    net_value = Column(Numeric(18, 8), nullable=False)

    portfolio = relationship("Portfolio", back_populates="dividends")
    asset = relationship("Asset")
