"""expand corporate events into a provider-neutral global catalog

Revision ID: 20260731_corp_event_catalog
Revises: 20260731_drop_legacy_divs
Create Date: 2026-07-31

Compatibility note:
This revision was applied by a preserved development branch before that branch
was split into smaller blocks. It remains in the canonical Alembic graph so
existing databases can be resolved safely. Runtime adoption of the expanded
catalog continues incrementally in separate commits.

Fresh-install note:
The preserved branch originally created ``corporate_events`` outside the
canonical Alembic graph. Fresh databases therefore reached this revision
without the legacy table. This migration now creates that legacy-compatible
base only when it is absent, then applies the original catalog expansion.
Existing databases are unchanged by the bootstrap step.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260731_corp_event_catalog"
down_revision: str = "20260731_drop_legacy_divs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _bootstrap_legacy_corporate_events_if_missing() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("corporate_events"):
        return

    op.create_table(
        "corporate_events",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDENTE"),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("ratio", sa.Numeric(20, 8), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("brapi_event_id", sa.String(), nullable=True),
        sa.Column("raw_data", sa.String(), nullable=True),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("portfolio_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"]),
        sa.UniqueConstraint("brapi_event_id", name="uq_corporate_events_brapi_event_id"),
    )
    op.create_index("ix_corporate_events_id", "corporate_events", ["id"])
    op.create_index("ix_corporate_events_asset_id", "corporate_events", ["asset_id"])
    op.create_index("ix_corporate_events_ticker", "corporate_events", ["ticker"])


def upgrade() -> None:
    _bootstrap_legacy_corporate_events_if_missing()

    metadata_type = sa.JSON().with_variant(
        postgresql.JSONB(astext_type=sa.Text()), "postgresql"
    )
    op.add_column("assets", sa.Column("isin_code", sa.String(32), nullable=True))
    op.create_index("ix_assets_isin_code", "assets", ["isin_code"])
    columns = (
        sa.Column("destination_asset_id", sa.Integer(), nullable=True),
        sa.Column("reconciliation_status", sa.String(), nullable=True),
        sa.Column("requires_review", sa.Boolean(), nullable=True),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("source_provider", sa.String(40), nullable=True),
        sa.Column("source_event_id", sa.String(160), nullable=True),
        sa.Column("source_payload_hash", sa.String(64), nullable=True),
        sa.Column("economic_identity_hash", sa.String(64), nullable=True),
        sa.Column("reconciliation_group_hash", sa.String(64), nullable=True),
        sa.Column("matched_event_id", sa.Integer(), nullable=True),
        sa.Column("is_canonical", sa.Boolean(), nullable=True),
        sa.Column("destination_ticker", sa.String(), nullable=True),
        sa.Column("isin_code", sa.String(32), nullable=True),
        sa.Column("destination_isin_code", sa.String(32), nullable=True),
        sa.Column("announcement_date", sa.Date(), nullable=True),
        sa.Column("approved_on", sa.Date(), nullable=True),
        sa.Column("record_date", sa.Date(), nullable=True),
        sa.Column("ex_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("quantity_factor", sa.Numeric(24, 12), nullable=True),
        sa.Column("cash_component", sa.Numeric(24, 8), nullable=True),
        sa.Column("subscription_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("destination_cost_allocation", sa.Numeric(12, 10), nullable=True),
        sa.Column("quantity_step", sa.Numeric(24, 12), nullable=True),
        sa.Column("fractional_settlement_price", sa.Numeric(24, 8), nullable=True),
        sa.Column("cash_treatment", sa.String(40), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("raw_metadata", metadata_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in columns:
        op.add_column("corporate_events", column)

    op.create_foreign_key(
        "fk_corporate_events_reviewer",
        "corporate_events",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_corporate_events_destination_asset",
        "corporate_events",
        "assets",
        ["destination_asset_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_corporate_events_matched_event",
        "corporate_events",
        "corporate_events",
        ["matched_event_id"],
        ["id"],
    )
    op.execute(
        """
        UPDATE corporate_events
           SET source_provider = 'legacy',
               source_event_id = brapi_event_id,
               reconciliation_status = 'UNRECONCILED',
               requires_review = TRUE,
               is_canonical = TRUE,
               effective_date = event_date,
               quantity_factor = ratio,
               currency = 'BRL',
               created_at = CURRENT_TIMESTAMP,
               updated_at = CURRENT_TIMESTAMP
        """
    )
    for name in (
        "source_provider",
        "reconciliation_status",
        "requires_review",
        "is_canonical",
        "effective_date",
        "quantity_factor",
        "currency",
        "created_at",
        "updated_at",
    ):
        op.alter_column("corporate_events", name, nullable=False)

    op.create_unique_constraint(
        "uq_corporate_events_source_identity",
        "corporate_events",
        ["source_provider", "source_event_id"],
    )
    op.create_index(
        "ix_corporate_events_economic_identity",
        "corporate_events",
        ["economic_identity_hash"],
    )
    op.create_index(
        "ix_corporate_events_reconciliation_group",
        "corporate_events",
        ["reconciliation_group_hash"],
    )
    op.create_index(
        "ix_corporate_events_asset_effective",
        "corporate_events",
        ["asset_id", "effective_date"],
    )
    op.create_index(
        "ix_corporate_events_event_type",
        "corporate_events",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_corporate_events_event_type", table_name="corporate_events")
    op.drop_index("ix_corporate_events_asset_effective", table_name="corporate_events")
    op.drop_index(
        "ix_corporate_events_economic_identity", table_name="corporate_events"
    )
    op.drop_index(
        "ix_corporate_events_reconciliation_group", table_name="corporate_events"
    )
    op.drop_constraint(
        "fk_corporate_events_reviewer", "corporate_events", type_="foreignkey"
    )
    op.drop_constraint(
        "uq_corporate_events_source_identity", "corporate_events", type_="unique"
    )
    op.drop_constraint(
        "fk_corporate_events_destination_asset", "corporate_events", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_corporate_events_matched_event", "corporate_events", type_="foreignkey"
    )
    for name in (
        "review_note",
        "reviewed_by_user_id",
        "reviewed_at",
        "reconciled_at",
        "updated_at",
        "created_at",
        "raw_metadata",
        "currency",
        "subscription_price",
        "cash_treatment",
        "fractional_settlement_price",
        "quantity_step",
        "destination_cost_allocation",
        "cash_component",
        "quantity_factor",
        "payment_date",
        "effective_date",
        "ex_date",
        "record_date",
        "approved_on",
        "announcement_date",
        "destination_isin_code",
        "isin_code",
        "destination_ticker",
        "economic_identity_hash",
        "is_canonical",
        "matched_event_id",
        "reconciliation_group_hash",
        "source_payload_hash",
        "source_event_id",
        "source_provider",
        "review_reason",
        "requires_review",
        "reconciliation_status",
        "destination_asset_id",
    ):
        op.drop_column("corporate_events", name)
    op.drop_index("ix_assets_isin_code", table_name="assets")
    op.drop_column("assets", "isin_code")
