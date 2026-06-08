from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from decimal import Decimal
from datetime import date
import enum


class TreasuryType(str, enum.Enum):
    SELIC = "Tesouro Selic"
    PREFIXADO = "Tesouro Prefixado"
    PREFIXADO_JUROS = "Tesouro Prefixado com Juros Semestrais"
    IPCA = "Tesouro IPCA+"
    IPCA_JUROS = "Tesouro IPCA+ com Juros Semestrais"
    IGPM_JUROS = "Tesouro IGP-M+ com Juros Semestrais"
    RENDA_MAIS = "Tesouro Renda+"
    EDUCA_MAIS = "Tesouro Educa+"


class TreasuryInvestment(Base, TimestampMixin):
    __tablename__ = "treasury_investments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    treasury_type: Mapped[TreasuryType] = mapped_column(SAEnum(TreasuryType), nullable=False)
    brapi_name: Mapped[str] = mapped_column(String(100), nullable=False)  # nome exato da BRAPI
    date_purchase: Mapped[date] = mapped_column(Date, nullable=False)
    date_maturity: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)   # titulos comprados
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)  # preco unitario na compra
    invested_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    rate_at_purchase: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)  # taxa contratada
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Para IPCA+: armazena a parte prefixada separada
    spread_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Relacionamentos
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="treasury")

    def __repr__(self) -> str:
        return f"<Treasury id={self.id} type={self.treasury_type} maturity={self.date_maturity}>"
