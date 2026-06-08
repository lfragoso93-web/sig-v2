from sqlalchemy import Integer, Numeric, Date, Boolean, ForeignKey, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from decimal import Decimal
from datetime import date
import enum


class IRPFMarket(str, enum.Enum):
    ACOES = "ACOES"           # Mercado à vista — isenção R$20k/mês
    DAY_TRADE = "DAY_TRADE"   # Day Trade — alíquota 20%
    FII = "FII"               # FIIs — 20%
    ETF = "ETF"               # ETFs — 15%
    CRIPTO = "CRIPTO"         # Criptomoedas — tabela progressiva
    RENDA_FIXA = "RENDA_FIXA" # Renda Fixa — tabela regressiva
    STOCKS = "STOCKS"         # Stocks/ETF Internacionais — 15% a 22.5%


class IRPFRecord(Base, TimestampMixin):
    """
    Apuração mensal de IRPF por mercado.
    """
    __tablename__ = "irpf_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12
    market: Mapped[IRPFMarket] = mapped_column(SAEnum(IRPFMarket), nullable=False)

    gross_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    loss_offset: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))  # prejuízo compensado
    taxable_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    ir_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False, default=Decimal("0"))  # alíquota aplicada
    ir_due: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))  # IR a pagar
    ir_withheld: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))  # IRRF (retido na fonte)
    ir_to_pay: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))  # líquido a recolher (DARF)
    is_exempt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # ação < R$20k
    darf_code: Mapped[str | None] = mapped_column(String(10), nullable=True)  # código DARF


class IRPFLoss(Base, TimestampMixin):
    """
    Saldo de prejuízos acumulados por mercado para compensação futura.
    """
    __tablename__ = "irpf_losses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    market: Mapped[IRPFMarket] = mapped_column(SAEnum(IRPFMarket), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    accumulated_loss: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
