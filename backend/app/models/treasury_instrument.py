"""Typed metadata associated 1:1 with a canonical Treasury asset."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TreasuryInstrument(Base):
    __tablename__ = "treasury_instruments"

    asset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    commercial_name: Mapped[str | None] = mapped_column(String(255))
    bond_type: Mapped[str | None] = mapped_column(String(64))
    indexer: Mapped[str | None] = mapped_column(String(64))
    coupon_type: Mapped[str | None] = mapped_column(String(64))
    maturity_date: Mapped[date | None] = mapped_column(Date)
    official_code: Mapped[str | None] = mapped_column(String(100))
    issuer: Mapped[str | None] = mapped_column(String(100))
    trading_status: Mapped[str | None] = mapped_column(String(32))
    metadata_source: Mapped[str | None] = mapped_column(String(64))
    source_reference: Mapped[str | None] = mapped_column(Text)
    source_observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    asset = relationship("Asset")
