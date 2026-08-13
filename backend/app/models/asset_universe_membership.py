"""Associações persistidas de ativos a universos operacionais externos."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class AssetUniverseMembership(Base):
    __tablename__ = "asset_universe_memberships"
    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "universe_key",
            name="uq_asset_universe_membership_asset_universe",
        ),
        Index(
            "ix_asset_universe_memberships_universe_rank",
            "universe_key",
            "rank",
        ),
    )

    id = Column(Integer, primary_key=True)
    asset_id = Column(
        Integer,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    universe_key = Column(String(64), nullable=False)
    rank = Column(Integer, nullable=True)
    source = Column(String(64), nullable=False)
    refreshed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    asset = relationship("Asset")
