from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime
import enum


class AssetType(str, enum.Enum):
    ACAO = "ACAO"
    FII = "FII"
    ETF_NACIONAL = "ETF_NACIONAL"
    ETF_INTERNACIONAL = "ETF_INTERNACIONAL"
    STOCK = "STOCK"
    CRIPTO = "CRIPTO"
    TESOURO_DIRETO = "TESOURO_DIRETO"
    RENDA_FIXA = "RENDA_FIXA"
    BDR = "BDR"
    OUTRO = "OUTRO"


class AssetCurrency(str, enum.Enum):
    BRL = "BRL"
    USD = "USD"
    EUR = "EUR"
    BTC = "BTC"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    asset_type = Column(String, nullable=False)
    currency = Column(String, default="BRL")
    last_price = Column(Numeric(18, 8), nullable=True)
    last_price_updated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    brapi_ticker = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    sub_sector = Column(String, nullable=True)
    float_description = Column(Float, nullable=True)

    positions = relationship("PortfolioPosition", back_populates="asset")
    prices = relationship("AssetPrice", back_populates="asset")
    asset_dividends = relationship("AssetDividend", back_populates="asset")
