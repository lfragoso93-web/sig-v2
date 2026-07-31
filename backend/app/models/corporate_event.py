from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class CorporateEventType(str, enum.Enum):
    DESDOBRAMENTO = "DESDOBRAMENTO"
    GRUPAMENTO = "GRUPAMENTO"
    BONIFICACAO = "BONIFICACAO"
    SUBSCRICAO = "SUBSCRICAO"
    TICKER_CHANGE = "TICKER_CHANGE"


class CorporateEventStatus(str, enum.Enum):
    PENDENTE = "PENDENTE"
    APLICADO = "APLICADO"
    IGNORADO = "IGNORADO"


class CorporateEvent(Base):
    __tablename__ = "corporate_events"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDENTE")
    event_date = Column(Date, nullable=False)
    ratio = Column(Numeric(20, 8), nullable=False)
    description = Column(String)
    brapi_event_id = Column(String, nullable=True, unique=True)
    raw_data = Column(String, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)

    portfolio = relationship("Portfolio", back_populates="corporate_events")
