from sqlalchemy import Numeric, DateTime, ForeignKey, UniqueConstraint, String, Index, desc
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from decimal import Decimal
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.asset import Asset


class AssetPrice(Base):
    """
    Histórico de preços de ativos. Alimentado pelo scheduler via BRAPI.
    """
    __tablename__ = "asset_prices"
    __table_args__ = (
        UniqueConstraint("asset_id", "timestamp", name="uq_price_asset_timestamp"),
        Index("idx_ap_asset_ts", "asset_id", desc("timestamp")),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    open: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    high: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    low: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 2), nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="brapi", nullable=False)

    # Relacionamentos
    asset: Mapped["Asset"] = relationship("Asset", back_populates="prices")

    def __repr__(self) -> str:
        return f"<AssetPrice asset={self.asset_id} close={self.close} ts={self.timestamp}>"
