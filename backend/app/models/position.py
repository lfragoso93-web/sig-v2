from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Position(Base):
    __tablename__ = "positions"

    id           = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker       = Column(String(20), nullable=False, index=True)
    asset_type   = Column(String(50), nullable=False)
    quantity     = Column(Float, nullable=False, default=0.0)
    avg_price    = Column(Float, nullable=False, default=0.0)
    # current_price e current_value s\u00e3o preenchidos dinamicamente via BRAPI
    current_price = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)

    portfolio = relationship("Portfolio", back_populates="positions")
