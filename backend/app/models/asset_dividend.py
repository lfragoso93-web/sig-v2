"""
AssetDividend — proventos declarados por ativo (fonte da verdade global).
Independente de carteira.
"""
from sqlalchemy import (
    Integer, Numeric, Date, String, ForeignKey, Text,
    UniqueConstraint, Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.dividend import DividendType
from decimal import Decimal
from datetime import date as DateType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.dividend import Dividend


class AssetDividend(Base):
    """
    Provento/evento corporativo declarado pelo ativo (global, sem vínculo com carteira).

    Datas:
      - record_date: Data Com / último dia com direito ao evento (BRAPI lastDatePrior)
      - ex_date: Data Ex / primeiro dia negociado sem direito; quando a fonte não
        fornece explicitamente, é derivada do próximo dia útil após record_date.
      - payment_date: Data de pagamento, quando aplicável.
      - approved_on: Data de aprovação/divulgação, quando disponível.

    Eventos suportados:
      - dinheiro: dividendos, JCP, rendimentos, amortizações
      - corporativos: bonificações e subscrições, preservando fator e payload bruto
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
    approved_on: Mapped[DateType | None] = mapped_column(Date, nullable=True)

    dividend_type: Mapped[DividendType] = mapped_column(
        SAEnum(DividendType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DividendType.DIVIDENDO,
    )

    value_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(18, 8), nullable=False
    )
    gross_value_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    factor: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)
    complete_factor: Mapped[Decimal | None] = mapped_column(Numeric(24, 12), nullable=True)

    isin_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    asset_issued: Mapped[str | None] = mapped_column(String(32), nullable=True)
    related_to: Mapped[str | None] = mapped_column(String(80), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

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
