"""Gates para o catálogo canônico de corporate_events refletido no MetaData."""

from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

from app.models.corporate_event import CorporateEvent


def _indexes() -> dict[str, object]:
    return {index.name: index for index in CorporateEvent.__table__.indexes}


def test_corporate_event_metadata_preserves_catalog_indexes() -> None:
    indexes = _indexes()

    for name in (
        "ix_corporate_events_economic_identity",
        "ix_corporate_events_reconciliation_group",
        "ix_corporate_events_asset_effective",
        "ix_corporate_events_event_type",
    ):
        assert name in indexes


def test_corporate_event_metadata_preserves_source_identity_constraint() -> None:
    constraints = {
        constraint.name: constraint
        for constraint in CorporateEvent.__table__.constraints
        if constraint.name
    }
    constraint = constraints["uq_corporate_events_source_identity"]

    assert [column.name for column in constraint.columns] == [
        "source_provider",
        "source_event_id",
    ]


def test_corporate_event_raw_metadata_uses_jsonb_on_postgresql() -> None:
    column_type = CorporateEvent.__table__.c.raw_metadata.type
    postgres_impl = column_type.dialect_impl(postgresql.dialect())

    assert isinstance(postgres_impl, JSONB)
