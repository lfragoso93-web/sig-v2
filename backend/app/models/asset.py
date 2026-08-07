import enum

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.datetime_utils import utc_now_naive


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

    __table_args__ = (
        UniqueConstraint("ticker", "asset_type", name="uq_assets_ticker_asset_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    asset_type = Column(String, nullable=False)
    currency = Column(String, default="BRL")
    last_price = Column(Numeric(18, 8), nullable=True)
    last_price_updated_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    brapi_ticker = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    sub_sector = Column(String, nullable=True)
    float_description = Column(Float, nullable=True)
    logo_url = Column(String, nullable=True)
    isin_code = Column(String(32), nullable=True, index=True)

    # Cache persistente do roteamento de mercado.
    provider = Column(String, nullable=True)
    provider_symbol = Column(String, nullable=True)
    provider_status = Column(String, nullable=True, index=True)
    provider_last_sync_at = Column(DateTime(timezone=True), nullable=True)
    provider_last_error = Column(String, nullable=True)
    provider_attempts = Column(Integer, nullable=False, default=0)

    positions = relationship("PortfolioPosition", back_populates="asset")
    prices = relationship("AssetPrice", back_populates="asset")
    asset_dividends = relationship("AssetDividend", back_populates="asset")
