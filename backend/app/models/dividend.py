import enum
from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.core.database import Base


class DividendType(str, enum.Enum):
    DIVIDENDO = "DIVIDENDO"
    JCP = "JCP"
    RENDIMENTO = "RENDIMENTO"
    AMORTIZACAO = "AMORTIZACAO"
    BONIFICACAO = "BONIFICACAO"
    OUTROS = "OUTROS"


class DividendStatus(str, enum.Enum):
    RECEBIDO = "RECEBIDO"
    PENDENTE = "PENDENTE"
    CANCELADO = "CANCELADO"
    A_RECEBER = "A_RECEBER"


class Dividend(Base):
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    asset_dividend_id = Column(Integer, ForeignKey("asset_dividends.id", ondelete="CASCADE"), nullable=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Numeric(20, 8), nullable=True)
    total_value = Column(Numeric(20, 8), nullable=True)
    net_value = Column(Numeric(20, 8), nullable=True)
    status = Column(
        SAEnum(
            DividendStatus,
            values_callable=lambda x: [e.value for e in x],
            native_enum=False,   # armazena como VARCHAR — sem tipo PG nativo
        ),
        nullable=False,
        default="RECEBIDO",
    )
    # campos legados (backfill)
    ticker = Column(String, nullable=True, index=True)
    ex_date = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=True)
    value_per_unit = Column(Numeric(20, 8), nullable=True)
    total_received = Column(Numeric(20, 8), nullable=True)
    dividend_type = Column(String, nullable=True)

    portfolio = relationship("Portfolio", back_populates="dividends")
    asset_dividend = relationship("AssetDividend", back_populates="portfolio_dividends")
