"""Officially sourced market-calendar facts used by financial projections."""
from datetime import date as DateType, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class MarketCalendarDay(Base):
    __tablename__ = "market_calendar_days"
    __table_args__ = (
        UniqueConstraint("market", "calendar_date", name="uq_market_calendar_day"),
        Index("ix_market_calendar_days_market_date", "market", "calendar_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    calendar_date: Mapped[DateType] = mapped_column(Date, nullable=False)
    is_business_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
