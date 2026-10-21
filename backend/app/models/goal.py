from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # tipo da meta
    # PATRIMONIO | PROVENTOS | RENTABILIDADE | LIVRE
    goal_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="LIVRE",
        server_default="LIVRE",
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # valor alvo informado pelo usuário
    target_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    # data alvo (opcional — informada manualmente ou calculada automaticamente)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # valor atual (snapshot na criação; atualizado em LIVRE)
    current_value: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # valor base na criação (calcula progresso relativo)
    base_value: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    # aporte mensal projetado pelo usuário (para calcular data projetada)
    monthly_contribution: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )

    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="goals",
    )
