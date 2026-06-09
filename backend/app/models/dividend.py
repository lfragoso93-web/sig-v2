from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class DividendType(str, enum.Enum):
    DIVIDENDO   = "dividendo"
    JCP         = "jcp"
    RENDIMENTO  = "rendimento"
    AMORTIZACAO = "amortizacao"
    BONIFICACAO = "bonificacao"
    OUTROS      = "outros"
    # aliases lowercase para compatibilidade com routers antigos
    dividendo   = "dividendo"
    jcp         = "jcp"
    rendimento  = "rendimento"
    amortizacao = "amortizacao"
    outro       = "outros"


class DividendStatus(str, enum.Enum):
    RECEBIDO  = "recebido"
    A_RECEBER = "a_receber"


class Dividend(Base):
    __tablename__ = "dividends"

    id           = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    # asset_id pode ser nulo para manter compatibilidade com registros manuais (ticker-based)
    asset_id     = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    ticker       = Column(String(20), nullable=True, index=True)
    asset_type   = Column(String(50), nullable=True)
    dividend_type = Column("type", SAEnum(DividendType, values_callable=lambda x: [e.value for e in x]), nullable=True)
    status       = Column(SAEnum(DividendStatus), nullable=True, default=DividendStatus.A_RECEBER)
    amount       = Column(Float, nullable=True)   # valor por cota (alias antigo)
    value_per_unit = Column(Float, nullable=True) # valor por cota (novo)
    total_value  = Column(Float, nullable=True)
    net_value    = Column(Float, nullable=True)
    quantity     = Column(Float, nullable=False, default=0)
    payment_date = Column(Date, nullable=True, index=True)
    ex_date      = Column(Date, nullable=True)

    portfolio = relationship("Portfolio", back_populates="dividends")
