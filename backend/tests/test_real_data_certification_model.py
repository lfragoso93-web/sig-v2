"""Metadata tests for the real-data certification event contract."""

from app.models.real_data_certification_event import RealDataCertificationEvent


def test_certification_event_is_registered_as_dedicated_table() -> None:
    table = RealDataCertificationEvent.__table__

    assert RealDataCertificationEvent.__tablename__ == (
        "real_data_certification_events"
    )
    assert "event_key" in table.c
    assert "supersedes_event_id" in table.c
    assert table.c.evidence_payload.nullable is False
    assert table.c.created_at.nullable is False
