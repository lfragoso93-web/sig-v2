from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime


class IRPFReport(Base):
    __tablename__ = "irpf_reports"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    year = Column(Integer, nullable=False)  # ano de referência
    data = Column(String, nullable=True)  # JSON serializado
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="irpf_reports")
