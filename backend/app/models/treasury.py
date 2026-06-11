from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from decimal import Decimal
from datetime import date
from typing import Optional


class TreasuryInvestment(Base, TimestampMixin):
    """
    Representa um investimento em Tesouro Direto.
    Modelo simplificado: o usuario informa valor investido, datas e nome do titulo.
    Cotacao atual e PL sao calculados on-the-fly via BRAPI.
    """
    __tablename__ = "treasury_investments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    brapi_name: Mapped[str] = mapped_column(String(100), nullable=False)  # nome exato/slug da BRAPI
    invested_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)  # valor investido em R$
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    maturity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relacionamentos
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="treasury")

    def __repr__(self) -> str:
        return f"<Treasury id={self.id} name={self.brapi_name} active={self.is_active}>"
