"""
AssetDividend — proventos declarados por ativo (fonte da verdade global).
Independente de carteira. Chave unica: (asset_id, ex_date, dividend_type).
"""
from sqlalchemy import (
    Integer, Numeric, Date, String, ForeignKey,
    UniqueConstraint, Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.dividend import DividendType
from decimal import Decimal
from datetime import date as DateType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.dividend import Dividend


class AssetDividend(Base):
    """
    Provento declarado pelo ativo (global, sem vinculo com carteira).
    Alimentado pelo backfill_service via BRAPI / yfinance.

    Datas:
      - record_date: data com / ultimo dia para manter o ativo com direito ao provento
      - ex_date: data ex / primeiro dia negociado sem direito ao provento
      - payment_date: data de pagamento
    """
    __tablename__ = "asset_dividends"
    __table_args__ = (
        UniqueConstraint(
            "asset_id", "ex_date", "dividend_type",
            name="uq_asset_dividend_asset_exdate_type"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    asset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    record_date: Mapped[DateType | None] = mapped_column(Date, nullable=True, index=True)
    ex_date: Mapped[DateType] = mapped_column(Date, nullable=False, index=True)
    payment_date: Mapped[DateType | None] = mapped_column(Date, nullable=True)

    dividend_type: Mapped[DividendType] = mapped_column(
        SAEnum(DividendType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DividendType.DIVIDENDO,
    )

    value_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(18, 8), nullable=False
    )

    source: Mapped[str] = mapped_column(
        String(30), nullable=False, default="brapi"
    )

    # Relacionamentos
    asset: Mapped["Asset"] = relationship("Asset", back_populates="asset_dividends")
    portfolio_dividends: Mapped[list["Dividend"]] = relationship(
        "Dividend", back_populates="asset_dividend", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<AssetDividend asset_id={self.asset_id} "
            f"com={self.record_date} ex={self.ex_date} type={self.dividend_type} "
            f"val={self.value_per_unit}>"
        )
