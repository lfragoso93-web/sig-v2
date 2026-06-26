from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime


class Goal(Base):
    __tablename__ = "goals"

    id              = Column(Integer, primary_key=True, index=True)
    portfolio_id    = Column(Integer, ForeignKey("portfolios.id"), nullable=False)

    # tipo da meta
    # PATRIMONIO | PROVENTOS | RENTABILIDADE | LIVRE
    goal_type       = Column(String, nullable=False, default="LIVRE")

    name            = Column(String, nullable=False)
    description     = Column(String, nullable=True)

    # valor alvo informado pelo usuário
    target_value    = Column(Float, nullable=False)

    # valor atual (snapshot no momento da criação; atualizado manualmente em LIVRE)
    current_value   = Column(Float, default=0.0)

    # valor base no momento da criação (usado para calcular progresso relativo)
    base_value      = Column(Float, default=0.0)

    # aporte mensal projetado pelo usuário (usado para calcular data projetada)
    monthly_contribution = Column(Float, nullable=True)

    # data alvo (opcional — informada manualmente ou calculada automaticamente)
    target_date     = Column(DateTime, nullable=True)

    created_at      = Column(DateTime, default=datetime.datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="goals")
