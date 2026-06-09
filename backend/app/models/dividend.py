from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class DividendType(str, enum.Enum):
    dividendo   = "dividendo"
    jcp         = "jcp"
    rendimento  = "rendimento"
    amortizacao = "amortizacao"
    outro       = "outro"


class Dividend(Base):
    __tablename__ = "dividends"

    id           = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker       = Column(String(20), nullable=False, index=True)
    asset_type   = Column(String(50), nullable=False)
    type         = Column(SAEnum(DividendType), nullable=False)
    amount       = Column(Float, nullable=False)   # valor por cota
    quantity     = Column(Float, nullable=False)   # qtd de cotas
    payment_date = Column(Date, nullable=False, index=True)
    ex_date      = Column(Date, nullable=True)

    portfolio = relationship("Portfolio", back_populates="dividends")
