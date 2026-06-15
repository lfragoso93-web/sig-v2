from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class CorporateEvent(Base):
    __tablename__ = "corporate_events"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)  # SPLIT, REVERSE_SPLIT, BONUS
    event_date = Column(Date, nullable=False)
    ratio = Column(Float, nullable=False)  # ex: 2.0 para 1:2
    description = Column(String)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)

    portfolio = relationship("Portfolio", back_populates="corporate_events")
