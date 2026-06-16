from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    name = Column(String, nullable=False)
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0.0)
    target_date = Column(DateTime, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="goals")
