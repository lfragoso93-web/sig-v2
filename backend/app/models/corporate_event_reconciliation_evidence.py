"""Persisted evidence for an automatic corporate-event reconciliation decision."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class CorporateEventReconciliationEvidence(Base):
    """Evidence that authorized the canonical reconciliation of one event."""

    __tablename__ = "corporate_event_reconciliation_evidence"
    __table_args__ = (
        UniqueConstraint(
            "corporate_event_id",
            name="uq_corporate_event_reconciliation_evidence_event",
        ),
    )

    id = Column(Integer, primary_key=True)
    corporate_event_id = Column(
        Integer,
        ForeignKey("corporate_events.id"),
        nullable=False,
        index=True,
    )
    decision = Column(String(20), nullable=False)
    evidence_type = Column(String(40), nullable=False)
    evidence_reference = Column(Text, nullable=False)
    fractional_policy = Column(String(40), nullable=False)
    fractional_quantity = Column(Numeric(24, 12), nullable=True)
    fractional_settlement_price = Column(Numeric(24, 8), nullable=True)
    cash_treatment = Column(String(40), nullable=True)
    ledger_basis = Column(String(40), nullable=True)
    ledger_transformation_reference = Column(Text, nullable=True)
    ledger_quantity_factor = Column(Numeric(24, 12), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    corporate_event = relationship("CorporateEvent")
