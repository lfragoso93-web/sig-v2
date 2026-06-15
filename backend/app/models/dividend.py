import enum
from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class DividendType(str, enum.Enum):
    DIVIDENDO = "DIVIDENDO"
    JCP = "JCP"
    RENDIMENTO = "RENDIMENTO"
    AMORTIZACAO = "AMORTIZACAO"


class Dividend(Base):
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False, index=True)
    ex_date = Column(Date, nullable=False)
    payment_date = Column(Date, nullable=True)
    value_per_unit = Column(Numeric(20, 8), nullable=False)
    total_received = Column(Numeric(20, 8), nullable=True)
    dividend_type = Column(String, nullable=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)
    asset_dividend_id = Column(Integer, ForeignKey("asset_dividends.id"), nullable=True)

    portfolio = relationship("Portfolio", back_populates="dividends")
    asset_dividend = relationship("AssetDividend", back_populates="portfolio_dividends")
