from sqlalchemy import String, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
import enum


class AssetType(str, enum.Enum):
    ACAO = "ACAO"                         # Acao Nacional
    FII = "FII"                           # Fundo Imobiliario
    ETF_NACIONAL = "ETF_NACIONAL"         # ETF Nacional
    TESOURO_DIRETO = "TESOURO_DIRETO"     # Tesouro Direto
    STOCK = "STOCK"                       # Stock Internacional
    ETF_INTERNACIONAL = "ETF_INTERNACIONAL" # ETF Internacional
    CRIPTO = "CRIPTO"                     # Criptomoeda
    RENDA_FIXA = "RENDA_FIXA"            # Renda Fixa (CDB, LCI, LCA, etc.)


class AssetCurrency(str, enum.Enum):
    BRL = "BRL"
    USD = "USD"
    EUR = "EUR"
    BTC = "BTC"  # para pares de cripto em BTC


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("ticker", "asset_type", name="uq_asset_ticker_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(SAEnum(AssetType), nullable=False)
    currency: Mapped[AssetCurrency] = mapped_column(
        SAEnum(AssetCurrency), default=AssetCurrency.BRL, nullable=False
    )
    brapi_ticker: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relacionamentos
    # Nota: Transaction e Dividend nao tem FK para assets (usam ticker como string).
    # Apenas PortfolioPosition e AssetPrice tem FK real para assets.id.
    positions: Mapped[list["PortfolioPosition"]] = relationship(
        "PortfolioPosition", back_populates="asset"
    )
    prices: Mapped[list["AssetPrice"]] = relationship(
        "AssetPrice", back_populates="asset", cascade="all, delete-orphan"
    )
    asset_dividends: Mapped[list["AssetDividend"]] = relationship(
        "AssetDividend", back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset ticker={self.ticker} type={self.asset_type}>"
