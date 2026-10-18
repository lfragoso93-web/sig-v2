"""Portfolio-scoped contractual metadata for fixed-income transactions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction


class FixedIncomeContract(Base, TimestampMixin):
    """Contract identity and terms; financial position remains ledger-derived."""

    __tablename__ = "fixed_income_contracts"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id",
            "id",
            name="uq_fixed_income_contract_portfolio_id",
        ),
        CheckConstraint(
            "product_type IN ('CDB', 'RDB', 'LCI', 'LCA', 'LC', 'LIG', 'CRI', "
            "'CRA', 'DEBENTURE', 'DEBENTURE_INCENTIVADA', "
            "'LETRA_FINANCEIRA', 'OUTRO')",
            name="ck_fixed_income_contract_product_type",
        ),
        CheckConstraint(
            "rate_unit IS NULL OR rate_unit IN "
            "('PERCENT_OF_INDEXER', 'ANNUAL_PERCENT', 'ANNUAL_SPREAD_PERCENT')",
            name="ck_fixed_income_contract_rate_unit",
        ),
        CheckConstraint(
            "(rate_value IS NULL AND rate_unit IS NULL) OR "
            "(rate_value IS NOT NULL AND rate_unit IS NOT NULL)",
            name="ck_fixed_income_contract_rate_pair",
        ),
        CheckConstraint(
            "liquidity_type IS NULL OR liquidity_type IN "
            "('DAILY', 'AT_MATURITY', 'CONTRACTUAL', 'UNKNOWN')",
            name="ck_fixed_income_contract_liquidity_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_type: Mapped[str] = mapped_column(String(64), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(150), nullable=True)
    indexer: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rate_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    rate_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    liquidity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    grace_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    tax_exempt: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="BRL")

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="fixed_income_contract",
        primaryjoin=(
            "and_(FixedIncomeContract.portfolio_id == Transaction.portfolio_id, "
            "FixedIncomeContract.id == foreign(Transaction.fixed_income_contract_id))"
        ),
    )
