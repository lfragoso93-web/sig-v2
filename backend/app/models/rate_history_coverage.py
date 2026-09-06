"""Persisted proof that a benchmark interval was fetched successfully.

`rate_history` stores the observations themselves. This table stores the ranges
for which an explicit import completed without a failed provider window, so
financial read paths can distinguish proven coverage from partial/unknown data
without inventing a weekday/holiday calendar.
"""
from __future__ import annotations

from datetime import date as DateType, datetime

from sqlalchemy import CheckConstraint, Column, Date, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class RateHistoryCoverage(Base):
    __tablename__ = "rate_history_coverages"

    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_rate_history_coverages_range"),
        UniqueConstraint(
            "indicator",
            "start_date",
            "end_date",
            "source",
            name="uq_rate_history_coverages_identity",
        ),
        Index(
            "ix_rate_history_coverages_indicator_range",
            "indicator",
            "start_date",
            "end_date",
        ),
    )

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    indicator: str = Column(String(10), nullable=False)
    start_date: DateType = Column(Date, nullable=False)
    end_date: DateType = Column(Date, nullable=False)
    source: str = Column(String(32), nullable=False, default="BCB_SGS")
    created_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
