from sqlalchemy import String, Numeric, Date, Boolean, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from decimal import Decimal
from datetime import date
import enum


class FixedIncomeType(str, enum.Enum):
    CDB = "CDB"
    LCI = "LCI"
    LCA = "LCA"
    LCI_LCA = "LCI_LCA"
    CRI = "CRI"
    CRA = "CRA"
    DEBENTURE = "DEBENTURE"
    POUPANCA = "POUPANCA"
    OUTROS = "OUTROS"


class IndexerType(str, enum.Enum):
    CDI = "CDI"              # % do CDI (ex: 110% CDI)
    IPCA_PLUS = "IPCA_PLUS"  # IPCA + spread (ex: IPCA + 5%)
    SELIC = "SELIC"          # % da SELIC
    PREFIXADO = "PREFIXADO"  # taxa fixa ao ano
    IGPM_PLUS = "IGPM_PLUS"  # IGP-M + spread


class FixedIncomeInvestment(Base, TimestampMixin):
    __tablename__ = "fixed_income_investments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    institution: Mapped[str] = mapped_column(String(150), nullable=False)
    fixed_income_type: Mapped[FixedIncomeType] = mapped_column(SAEnum(FixedIncomeType), nullable=False)
    indexer: Mapped[IndexerType] = mapped_column(SAEnum(IndexerType), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    invested_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    date_start: Mapped[date] = mapped_column(Date, nullable=False)

    # Se daily_liquidity=True o título pode ser resgatado a qualquer dia
    # e date_maturity deve ser None (sem carência/vencimento relevante).
    daily_liquidity: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    date_maturity: Mapped[date | None] = mapped_column(Date, nullable=True)  # None quando daily_liquidity=True

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_ir_exempt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # LCI/LCA isentos
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="fixed_income")

    def __repr__(self) -> str:
        return f"<FixedIncome id={self.id} name={self.name} indexer={self.indexer} daily_liquidity={self.daily_liquidity}>"
