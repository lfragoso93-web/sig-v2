import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

_RAW_METADATA_TYPE = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")


class CorporateEventType(str, enum.Enum):
    DESDOBRAMENTO = "DESDOBRAMENTO"
    GRUPAMENTO = "GRUPAMENTO"
    BONIFICACAO = "BONIFICACAO"
    SUBSCRICAO = "SUBSCRICAO"
    TICKER_CHANGE = "TICKER_CHANGE"


class CorporateEventStatus(str, enum.Enum):
    PENDENTE = "PENDENTE"
    APLICADO = "APLICADO"
    IGNORADO = "IGNORADO"


class CorporateEvent(Base):
    __tablename__ = "corporate_events"
    __table_args__ = (
        UniqueConstraint(
            "source_provider",
            "source_event_id",
            name="uq_corporate_events_source_identity",
        ),
        CheckConstraint(
            "(source_quantity_factor IS NULL AND source_cost_allocation IS NULL) "
            "OR (source_quantity_factor IS NOT NULL "
            "AND source_cost_allocation IS NOT NULL)",
            name="ck_corporate_event_source_transform_pair",
        ),
        CheckConstraint(
            "source_quantity_factor IS NULL OR source_quantity_factor >= 0",
            name="ck_corporate_event_source_quantity_factor_nonnegative",
        ),
        CheckConstraint(
            "source_cost_allocation IS NULL OR "
            "source_cost_allocation BETWEEN 0 AND 1",
            name="ck_corporate_event_source_cost_allocation_range",
        ),
        Index(
            "ix_corporate_events_economic_identity",
            "economic_identity_hash",
        ),
        Index(
            "ix_corporate_events_reconciliation_group",
            "reconciliation_group_hash",
        ),
        Index(
            "ix_corporate_events_asset_effective",
            "asset_id",
            "effective_date",
        ),
        Index("ix_corporate_events_event_type", "event_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PENDENTE")

    # Contratos legados preservados temporariamente durante a migração incremental.
    event_date = Column(Date, nullable=False)
    ratio = Column(Numeric(20, 8), nullable=False)
    description = Column(String)
    brapi_event_id = Column(String, nullable=True, unique=True)
    raw_data = Column(String, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True)

    # Catálogo canônico independente de provedor.
    destination_asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    reconciliation_status = Column(
        String,
        nullable=False,
        default="UNRECONCILED",
    )
    requires_review = Column(Boolean, nullable=False, default=True)
    review_reason = Column(Text, nullable=True)
    source_provider = Column(String(40), nullable=False, default="legacy")
    source_event_id = Column(String(160), nullable=True)
    source_payload_hash = Column(String(64), nullable=True)
    economic_identity_hash = Column(String(64), nullable=True)
    reconciliation_group_hash = Column(String(64), nullable=True)
    matched_event_id = Column(
        Integer,
        ForeignKey("corporate_events.id"),
        nullable=True,
    )
    is_canonical = Column(Boolean, nullable=False, default=True)
    destination_ticker = Column(String, nullable=True)
    isin_code = Column(String(32), nullable=True)
    destination_isin_code = Column(String(32), nullable=True)
    announcement_date = Column(Date, nullable=True)
    approved_on = Column(Date, nullable=True)
    record_date = Column(Date, nullable=True)
    ex_date = Column(Date, nullable=True)
    effective_date = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=True)
    quantity_factor = Column(Numeric(24, 12), nullable=False)
    cash_component = Column(Numeric(24, 8), nullable=True)
    subscription_price = Column(Numeric(24, 8), nullable=True)
    destination_cost_allocation = Column(Numeric(12, 10), nullable=True)
    source_quantity_factor = Column(Numeric(24, 12), nullable=True)
    source_cost_allocation = Column(Numeric(12, 10), nullable=True)
    quantity_step = Column(Numeric(24, 12), nullable=True)
    fractional_settlement_price = Column(Numeric(24, 8), nullable=True)
    cash_treatment = Column(String(40), nullable=True)
    currency = Column(String(8), nullable=False, default="BRL")
    raw_metadata = Column(_RAW_METADATA_TYPE, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_note = Column(Text, nullable=True)
    reconciled_at = Column(DateTime(timezone=True), nullable=True)

    portfolio = relationship("Portfolio", back_populates="corporate_events")
    destination_legs = relationship(
        "CorporateEventDestinationLeg",
        back_populates="corporate_event",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="CorporateEventDestinationLeg.destination_isin_code",
    )


class CorporateEventDestinationLeg(Base):
    """Resolved, evidenced destination security for a complex event."""

    __tablename__ = "corporate_event_destination_legs"
    __table_args__ = (
        UniqueConstraint(
            "corporate_event_id",
            "destination_isin_code",
            name="uq_corp_event_destination_leg_isin",
        ),
        CheckConstraint(
            "length(trim(destination_isin_code)) = 12",
            name="ck_corp_event_destination_leg_isin_length",
        ),
        CheckConstraint(
            "destination_isin_code = upper(trim(destination_isin_code))",
            name="ck_corp_event_destination_leg_isin_normalized",
        ),
        CheckConstraint(
            "quantity_factor > 0",
            name="ck_corp_event_destination_leg_factor_positive",
        ),
        CheckConstraint(
            "cost_allocation BETWEEN 0 AND 1",
            name="ck_corp_event_destination_leg_cost_range",
        ),
        CheckConstraint(
            "length(trim(evidence_reference)) > 0",
            name="ck_corp_event_destination_leg_evidence_nonempty",
        ),
    )

    id = Column(Integer, primary_key=True)
    corporate_event_id = Column(
        Integer,
        ForeignKey("corporate_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    destination_asset_id = Column(
        Integer,
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    destination_ticker = Column(String, nullable=True)
    destination_isin_code = Column(String(32), nullable=False)
    quantity_factor = Column(Numeric(24, 12), nullable=False)
    cost_allocation = Column(Numeric(12, 10), nullable=False)
    evidence_reference = Column(Text, nullable=False)

    corporate_event = relationship(
        "CorporateEvent", back_populates="destination_legs"
    )
