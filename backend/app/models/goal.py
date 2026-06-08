from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, Enum as SAEnum, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from decimal import Decimal
from datetime import date
import enum


class GoalType(str, enum.Enum):
    PATRIMONIO_ALVO = "PATRIMONIO_ALVO"       # alcançar X de patrimônio
    ALOCACAO = "ALOCACAO"                     # manter alocação por classe
    DY_MENSAL = "DY_MENSAL"                   # renda passiva mensal alvo
    RENTABILIDADE = "RENTABILIDADE"           # rentabilidade mínima
    APORTE_MENSAL = "APORTE_MENSAL"           # aporte mensal alvo


class Goal(Base, TimestampMixin):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    goal_type: Mapped[GoalType] = mapped_column(SAEnum(GoalType), nullable=False)
    target_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relacionamentos
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="goals")
    allocations: Mapped[list["GoalAllocation"]] = relationship(
        "GoalAllocation", back_populates="goal", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Goal id={self.id} type={self.goal_type} target={self.target_value}>"


class GoalAllocation(Base, TimestampMixin):
    """
    Distribuição percentual alvo por classe de ativo dentro de uma meta de alocação.
    """
    __tablename__ = "goal_allocations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    goal_id: Mapped[int] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)  # usa AssetType enum value
    target_percentage: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)  # ex: 30.000 = 30%

    # Relacionamentos
    goal: Mapped["Goal"] = relationship("Goal", back_populates="allocations")
