from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.corporate_event import CorporateEvent
    from app.models.goal import Goal
    from app.models.portfolio_class_snapshot import PortfolioClassSnapshot
    from app.models.portfolio_class_target import PortfolioClassTarget
    from app.models.portfolio_position import PortfolioPosition
    from app.models.portfolio_snapshot import PortfolioSnapshot
    from app.models.transaction import Transaction
    from app.models.user import User


class Portfolio(Base, TimestampMixin):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="portfolios")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="portfolio", cascade="all, delete-orphan"
    )
    positions: Mapped[list["PortfolioPosition"]] = relationship(
        "PortfolioPosition", back_populates="portfolio", cascade="all, delete-orphan"
    )
    goals: Mapped[list["Goal"]] = relationship(
        "Goal", back_populates="portfolio", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["PortfolioSnapshot"]] = relationship(
        "PortfolioSnapshot", back_populates="portfolio", cascade="all, delete-orphan"
    )
    class_snapshots: Mapped[list["PortfolioClassSnapshot"]] = relationship(
        "PortfolioClassSnapshot",
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )
    corporate_events: Mapped[list["CorporateEvent"]] = relationship(
        "CorporateEvent", back_populates="portfolio", cascade="all, delete-orphan"
    )
    class_targets: Mapped[list["PortfolioClassTarget"]] = relationship(
        "PortfolioClassTarget", back_populates="portfolio", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Portfolio id={self.id} name={self.name} user_id={self.user_id}>"
