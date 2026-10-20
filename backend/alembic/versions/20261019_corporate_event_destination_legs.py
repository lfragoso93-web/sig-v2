"""add evidenced destination legs for complex corporate events

Revision ID: 20261019_corp_event_legs
Revises: 20261017_fixed_income_contracts
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20261019_corp_event_legs"
down_revision: str | None = "20261017_fixed_income_contracts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "corporate_events",
        sa.Column("source_quantity_factor", sa.Numeric(24, 12), nullable=True),
    )
    op.add_column(
        "corporate_events",
        sa.Column("source_cost_allocation", sa.Numeric(12, 10), nullable=True),
    )
    op.create_check_constraint(
        "ck_corporate_event_source_transform_pair",
        "corporate_events",
        "(source_quantity_factor IS NULL AND source_cost_allocation IS NULL) "
        "OR (source_quantity_factor IS NOT NULL "
        "AND source_cost_allocation IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_corporate_event_source_quantity_factor_nonnegative",
        "corporate_events",
        "source_quantity_factor IS NULL OR source_quantity_factor >= 0",
    )
    op.create_check_constraint(
        "ck_corporate_event_source_cost_allocation_range",
        "corporate_events",
        "source_cost_allocation IS NULL OR "
        "source_cost_allocation BETWEEN 0 AND 1",
    )

    op.create_table(
        "corporate_event_destination_legs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("corporate_event_id", sa.Integer(), nullable=False),
        sa.Column("destination_asset_id", sa.Integer(), nullable=True),
        sa.Column("destination_ticker", sa.String(), nullable=True),
        sa.Column("destination_isin_code", sa.String(length=32), nullable=False),
        sa.Column("quantity_factor", sa.Numeric(24, 12), nullable=False),
        sa.Column("cost_allocation", sa.Numeric(12, 10), nullable=False),
        sa.Column("evidence_reference", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "length(trim(destination_isin_code)) = 12",
            name="ck_corp_event_destination_leg_isin_length",
        ),
        sa.CheckConstraint(
            "destination_isin_code = upper(trim(destination_isin_code))",
            name="ck_corp_event_destination_leg_isin_normalized",
        ),
        sa.CheckConstraint(
            "quantity_factor > 0",
            name="ck_corp_event_destination_leg_factor_positive",
        ),
        sa.CheckConstraint(
            "cost_allocation BETWEEN 0 AND 1",
            name="ck_corp_event_destination_leg_cost_range",
        ),
        sa.CheckConstraint(
            "length(trim(evidence_reference)) > 0",
            name="ck_corp_event_destination_leg_evidence_nonempty",
        ),
        sa.ForeignKeyConstraint(
            ["corporate_event_id"],
            ["corporate_events.id"],
            name="fk_corp_event_destination_leg_event",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["destination_asset_id"],
            ["assets.id"],
            name="fk_corp_event_destination_leg_asset",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_corporate_event_destination_legs",
        ),
        sa.UniqueConstraint(
            "corporate_event_id",
            "destination_isin_code",
            name="uq_corp_event_destination_leg_isin",
        ),
    )
    op.create_index(
        "ix_corp_event_destination_leg_asset",
        "corporate_event_destination_legs",
        ["destination_asset_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    leg_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM corporate_event_destination_legs")
    ).scalar_one()
    resolved_source_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM corporate_events "
            "WHERE source_quantity_factor IS NOT NULL "
            "OR source_cost_allocation IS NOT NULL"
        )
    ).scalar_one()
    if leg_count or resolved_source_count:
        raise RuntimeError(
            "cannot downgrade while resolved corporate-event legs exist"
        )

    op.drop_index(
        "ix_corp_event_destination_leg_asset",
        table_name="corporate_event_destination_legs",
    )
    op.drop_table("corporate_event_destination_legs")
    op.drop_constraint(
        "ck_corporate_event_source_cost_allocation_range",
        "corporate_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_corporate_event_source_quantity_factor_nonnegative",
        "corporate_events",
        type_="check",
    )
    op.drop_constraint(
        "ck_corporate_event_source_transform_pair",
        "corporate_events",
        type_="check",
    )
    op.drop_column("corporate_events", "source_cost_allocation")
    op.drop_column("corporate_events", "source_quantity_factor")
