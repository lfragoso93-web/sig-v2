"""contract legacy corporate event columns (event_date, ratio, brapi_event_id, raw_data)

Revision ID: 20261021_contract_corp_events
Revises: 20261019_corp_event_legs
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261021_contract_corp_events"
down_revision: str | None = "20261019_corp_event_legs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "corporate_events"


def _assert_canonical_integrity(bind: sa.engine.Connection) -> None:
    # Ensure all rows have quantity_factor and source_event_id populated
    unbacked_count = int(
        bind.execute(
            sa.text(
                f"SELECT COUNT(*) FROM {_TABLE} "
                "WHERE quantity_factor IS NULL OR source_event_id IS NULL"
            )
        ).scalar_one()
    )
    if unbacked_count > 0:
        raise RuntimeError(
            f"physical contraction blocked: {_TABLE} contains {unbacked_count} rows "
            "missing canonical quantity_factor or source_event_id"
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE):
        return

    _assert_canonical_integrity(bind)

    columns = {col["name"] for col in inspector.get_columns(_TABLE)}

    # Drop unique constraint on brapi_event_id if it exists
    constraints = {c["name"] for c in inspector.get_unique_constraints(_TABLE)}
    if "uq_corporate_events_brapi_event_id" in constraints:
        op.drop_constraint(
            "uq_corporate_events_brapi_event_id",
            _TABLE,
            type_="unique",
        )

    # Drop legacy columns if present
    if "brapi_event_id" in columns:
        op.drop_column(_TABLE, "brapi_event_id")

    if "raw_data" in columns:
        op.drop_column(_TABLE, "raw_data")

    if "event_date" in columns:
        op.drop_column(_TABLE, "event_date")

    if "ratio" in columns:
        op.drop_column(_TABLE, "ratio")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE):
        return

    columns = {col["name"] for col in inspector.get_columns(_TABLE)}

    if "ratio" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("ratio", sa.Numeric(20, 8), nullable=True),
        )

    if "event_date" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("event_date", sa.Date(), nullable=True),
        )

    if "raw_data" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("raw_data", sa.String(), nullable=True),
        )

    if "brapi_event_id" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("brapi_event_id", sa.String(), nullable=True),
        )

    constraints = {c["name"] for c in inspector.get_unique_constraints(_TABLE)}
    if "uq_corporate_events_brapi_event_id" not in constraints:
        op.create_unique_constraint(
            "uq_corporate_events_brapi_event_id",
            _TABLE,
            ["brapi_event_id"],
        )

    # Repopulate restored columns from canonical values
    op.execute(
        sa.text(
            f"UPDATE {_TABLE} "
            "SET event_date = effective_date, ratio = quantity_factor "
            "WHERE effective_date IS NOT NULL"
        )
    )
