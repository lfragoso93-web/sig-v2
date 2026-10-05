"""Append-only audit contract for real-data readiness decisions."""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

_EVIDENCE_PAYLOAD_TYPE = JSON().with_variant(JSONB, "postgresql")


class RealDataCertificationEvent(Base):
    """One immutable promotion or revocation decision for an environment."""

    __tablename__ = "real_data_certification_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('PROMOTE', 'REVOKE')",
            name="ck_real_data_cert_events_action",
        ),
        UniqueConstraint(
            "event_key",
            name="uq_real_data_certification_events_event_key",
        ),
        Index(
            "ix_real_data_cert_events_environment_created_at",
            "environment",
            "created_at",
        ),
    )

    id = Column(Integer, primary_key=True)
    event_key = Column(String(64), nullable=False)
    action = Column(String(16), nullable=False)
    schema_version = Column(String(64), nullable=False)
    environment = Column(String(32), nullable=False)
    branch = Column(String(100), nullable=False)
    commit_sha = Column(String(40), nullable=False)
    dataset_reference = Column(Text, nullable=False)
    alembic_revision = Column(String(64), nullable=False)
    gate_issue_reference = Column(String(100), nullable=True)
    pull_request_reference = Column(String(100), nullable=True)
    evidence_sha256 = Column(String(64), nullable=False)
    evidence_payload = Column(_EVIDENCE_PAYLOAD_TYPE, nullable=False)
    actor = Column(String(200), nullable=False)
    reason = Column(Text, nullable=False)
    supersedes_event_id = Column(
        Integer,
        ForeignKey("real_data_certification_events.id"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    supersedes_event = relationship(
        "RealDataCertificationEvent",
        remote_side=[id],
        uselist=False,
    )
