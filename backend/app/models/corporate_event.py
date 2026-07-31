"""Catalogo global e independente de provedor de eventos corporativos."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class CorporateEventType(str, enum.Enum):
    DESDOBRAMENTO = "DESDOBRAMENTO"
    GRUPAMENTO = "GRUPAMENTO"
    BONIFICACAO = "BONIFICACAO"
    SUBSCRICAO = "SUBSCRICAO"
    TICKER_CHANGE = "TICKER_CHANGE"
    CONVERSION = "CONVERSION"
    INCORPORATION = "INCORPORATION"
    MERGER = "MERGER"
    SPINOFF = "SPINOFF"
    AMORTIZATION = "AMORTIZATION"
    DELISTING = "DELISTING"


class CorporateEventStatus(str, enum.Enum):
    PENDENTE = "PENDENTE"
    APLICADO = "APLICADO"
    IGNORADO = "IGNORADO"
    DISCOVERED = "DISCOVERED"
    PENDING_REVIEW = "PENDING_REVIEW"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class CorporateEventReconciliationStatus(str, enum.Enum):
    UNRECONCILED = "UNRECONCILED"
    MATCHED = "MATCHED"
    CONFLICT = "CONFLICT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    MANUALLY_VALIDATED = "MANUALLY_VALIDATED"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CorporateEvent(Base):
    __tablename__ = "corporate_events"
    __table_args__ = (
        UniqueConstraint(
            "source_provider",
            "source_event_id",
            name="uq_corporate_events_source_identity",
        ),
        Index("ix_corporate_events_economic_identity", "economic_identity_hash"),
        Index("ix_corporate_events_reconciliation_group", "reconciliation_group_hash"),
        Index(
            "ix_corporate_events_asset_effective",
            "asset_id",
            "effective_date",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    destination_asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)

    event_type = Column(String, nullable=False, index=True)
    status = Column(
        String, nullable=False, default=CorporateEventStatus.DISCOVERED.value
    )
    reconciliation_status = Column(
        String,
        nullable=False,
        default=CorporateEventReconciliationStatus.UNRECONCILED.value,
    )
    requires_review = Column(Boolean, nullable=False, default=True)
    review_reason = Column(Text, nullable=True)

    source_provider = Column(String(40), nullable=False)
    source_event_id = Column(String(160), nullable=True)
    source_payload_hash = Column(String(64), nullable=True)
    economic_identity_hash = Column(String(64), nullable=True)
    reconciliation_group_hash = Column(String(64), nullable=True)
    matched_event_id = Column(Integer, ForeignKey("corporate_events.id"), nullable=True)
    is_canonical = Column(Boolean, nullable=False, default=True)

    ticker = Column(String, nullable=False, index=True)
    destination_ticker = Column(String, nullable=True)
    isin_code = Column(String(32), nullable=True)
    destination_isin_code = Column(String(32), nullable=True)

    announcement_date = Column(Date, nullable=True)
    approved_on = Column(Date, nullable=True)
    record_date = Column(Date, nullable=True)
    ex_date = Column(Date, nullable=True)
    effective_date = Column(Date, nullable=False)
    payment_date = Column(Date, nullable=True)

    quantity_factor = Column(Numeric(24, 12), nullable=False)
    cash_component = Column(Numeric(24, 8), nullable=True)
    subscription_price = Column(Numeric(24, 8), nullable=True)
    destination_cost_allocation = Column(Numeric(12, 10), nullable=True)
    quantity_step = Column(Numeric(24, 12), nullable=True)
    fractional_settlement_price = Column(Numeric(24, 8), nullable=True)
    cash_treatment = Column(String(40), nullable=True)
    currency = Column(String(8), nullable=False, default="BRL")

    description = Column(Text, nullable=True)
    raw_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_note = Column(Text, nullable=True)
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    applied_at = Column(DateTime(timezone=True), nullable=True)

    # Compatibilidade temporaria com fluxos anteriores. Novas gravacoes devem
    # usar os campos canonicos acima; a remocao exige migration posterior.
    event_date = Column(Date, nullable=False)
    ratio = Column(Numeric(20, 8), nullable=False)
    brapi_event_id = Column(String, nullable=True, unique=True)
    raw_data = Column(String, nullable=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)

    portfolio = relationship("Portfolio", back_populates="corporate_events")
