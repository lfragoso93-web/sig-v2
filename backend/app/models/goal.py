from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        Index("ix_goals_portfolio_id", "portfolio_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(
        Integer,
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Contrato funcional atual da API/service.
    # Valores aceitos são validados no schema Pydantic.
    goal_type = Column(String(30), nullable=False, default="LIVRE")

    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)

    # Persistência exata em NUMERIC, mantendo floats no runtime do service atual.
    target_value: float = Column(Numeric(18, 2, asdecimal=False), nullable=False)
    current_value: float = Column(
        Numeric(18, 2, asdecimal=False),
        nullable=False,
        default=0.0,
        server_default=text("0"),
    )
    base_value: float = Column(
        Numeric(18, 2, asdecimal=False),
        nullable=False,
        default=0.0,
        server_default=text("0"),
    )
    monthly_contribution: float | None = Column(
        Numeric(18, 2, asdecimal=False), nullable=True
    )

    target_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=True, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=True, server_default=text("now()"))

    portfolio = relationship("Portfolio", back_populates="goals")
