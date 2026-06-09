from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Position(Base):
    """
    Modelo legado de posicao (tabela 'positions').
    Nao confundir com PortfolioPosition (tabela 'portfolio_positions') que e o modelo atual.
    O back_populates foi removido para evitar conflito com Portfolio.positions
    que aponta para PortfolioPosition.
    """
    __tablename__ = "positions"

    id            = Column(Integer, primary_key=True, index=True)
    portfolio_id  = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker        = Column(String(20), nullable=False, index=True)
    asset_type    = Column(String(50), nullable=False)
    quantity      = Column(Float, nullable=False, default=0.0)
    avg_price     = Column(Float, nullable=False, default=0.0)
    current_price = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)

    # Sem back_populates para evitar conflito com Portfolio.positions -> PortfolioPosition
    portfolio = relationship("Portfolio", foreign_keys=[portfolio_id])
