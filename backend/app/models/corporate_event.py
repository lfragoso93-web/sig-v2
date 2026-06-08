from sqlalchemy import Column, Integer, ForeignKey, Numeric, Date, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum
from sqlalchemy import Enum as SAEnum


class CorporateEventType(str, enum.Enum):
    DESDOBRAMENTO = "DESDOBRAMENTO"
    GRUPAMENTO = "GRUPAMENTO"
    BONIFICACAO = "BONIFICACAO"


class CorporateEventStatus(str, enum.Enum):
    PENDENTE = "PENDENTE"
    APLICADO = "APLICADO"
    IGNORADO = "IGNORADO"


class CorporateEvent(Base):
    __tablename__ = "corporate_events"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    event_type = Column(SAEnum(CorporateEventType), nullable=False)
    status = Column(SAEnum(CorporateEventStatus), default=CorporateEventStatus.PENDENTE, nullable=False)
    event_date = Column(Date, nullable=False)
    # Split 1:2 = ratio 2.0 | Grupamento 2:1 = ratio 0.5 | Bonificacao 10% = ratio 0.10
    ratio = Column(Numeric(18, 8), nullable=False)
    brapi_event_id = Column(String(150), nullable=True, unique=True)
    raw_data = Column(Text, nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    asset = relationship("Asset")
