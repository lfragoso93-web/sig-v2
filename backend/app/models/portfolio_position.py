from sqlalchemy import Numeric, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.portfolio import Portfolio


class PortfolioPosition(Base, TimestampMixin):
    """
    Posição consolidada de um ativo em uma carteira.
    Atualizada automaticamente a cada transação.
    """
    __tablename__ = "portfolio_positions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "asset_id", name="uq_position_portfolio_asset"),
        Index("idx_pp_portfolio", "portfolio_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, default=Decimal("0"))
    average_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, default=Decimal("0"))
    total_invested: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    # Lucro realizado acumulado (vendas)
    realized_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))

    # Relacionamentos
    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")
    asset: Mapped["Asset"] = relationship("Asset", back_populates="positions")

    def __repr__(self) -> str:
        return f"<Position portfolio={self.portfolio_id} asset={self.asset_id} qty={self.quantity}>"
