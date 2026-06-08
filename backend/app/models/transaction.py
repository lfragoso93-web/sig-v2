from sqlalchemy import (
    String, Numeric, Integer, Date, Text,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from decimal import Decimal
from datetime import date
import enum


class TransactionType(str, enum.Enum):
    COMPRA = "COMPRA"
    VENDA = "VENDA"
    DESDOBRAMENTO = "DESDOBRAMENTO"   # split
    GRUPAMENTO = "GRUPAMENTO"         # inplit
    BONIFICACAO = "BONIFICACAO"       # bonificação em ações
    TRANSFERENCIA_ENTRADA = "TRANSFERENCIA_ENTRADA"
    TRANSFERENCIA_SAIDA = "TRANSFERENCIA_SAIDA"


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)  # qty * unit_price
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    broker: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Para Day Trade — usado no IRPF
    is_day_trade: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relacionamentos
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="transactions")
    asset: Mapped["Asset"] = relationship("Asset", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type={self.transaction_type} asset_id={self.asset_id}>"
