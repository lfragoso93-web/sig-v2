from sqlalchemy import Numeric, Date, String, ForeignKey, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from decimal import Decimal
from datetime import date
import enum


class DividendType(str, enum.Enum):
    DIVIDENDO = "DIVIDENDO"
    JCP = "JCP"                    # Juros sobre Capital Próprio
    RENDIMENTO = "RENDIMENTO"      # FIIs
    AMORTIZACAO = "AMORTIZACAO"    # FIIs / CRIs
    FRACAO = "FRACAO"              # Fração de ação
    OUTROS = "OUTROS"


class Dividend(Base, TimestampMixin):
    __tablename__ = "dividends"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    dividend_type: Mapped[DividendType] = mapped_column(SAEnum(DividendType), nullable=False)
    date_ex: Mapped[date] = mapped_column(Date, nullable=False)        # data ex-dividendo
    date_payment: Mapped[date | None] = mapped_column(Date, nullable=True)  # data pagamento
    quantity_on_date: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    value_per_share: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    is_projected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # futuro
    ir_withheld: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)  # IR retido na fonte (JCP)

    # Relacionamentos
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="dividends")
    asset: Mapped["Asset"] = relationship("Asset", back_populates="dividends")

    def __repr__(self) -> str:
        return f"<Dividend asset={self.asset_id} total={self.total_value} date={self.date_ex}>"
