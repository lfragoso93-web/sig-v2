"""Snapshot diário de patrimônio e TWR por classe de ativo."""
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class PortfolioClassSnapshot(Base, TimestampMixin):
    __tablename__ = "portfolio_class_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "asset_type",
            "snapshot_date",
            name="uq_class_snapshot_portfolio_type_date",
        ),
        Index(
            "idx_pcs_portfolio_type_date_desc",
            "portfolio_id",
            "asset_type",
            "snapshot_date",
            postgresql_ops={"snapshot_date": "DESC"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(String(40), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))

    net_external_flow: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    dividends_day: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    dividends_accumulated: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    daily_return_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=Decimal("0"))
    accumulated_return_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=Decimal("0"))

    has_partial_prices: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    return_is_estimated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    valuation_status: Mapped[str] = mapped_column(String(40), nullable=False, default="complete")

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="class_snapshots")
