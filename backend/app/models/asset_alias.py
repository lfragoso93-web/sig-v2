"""Aliases historicos de tickers associados a um ativo atual."""

import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class AssetAlias(Base):
    __tablename__ = "asset_aliases"
    __table_args__ = (
        UniqueConstraint("alias_ticker", "asset_type", name="uq_asset_aliases_ticker_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    alias_ticker = Column(String, nullable=False, index=True)
    asset_type = Column(String, nullable=False)
    effective_from = Column(Date, nullable=True)
    effective_to = Column(Date, nullable=True)
    source_provider = Column(String, nullable=False, default="market_data_provider")
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    asset = relationship("Asset")
