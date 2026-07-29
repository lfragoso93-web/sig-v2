"""expand asset dividend economic identity

Revision ID: 20260729_expand_dividend_identity
Revises: 20260728_dividends_sync_jobs
Create Date: 2026-07-29

Permite eventos monetários legítimos do mesmo tipo e Data Ex quando o pagamento
efetivo difere, sem perder a unicidade física de uma mesma ocorrência.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260729_expand_dividend_identity"
down_revision: str = "20260728_dividends_sync_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_asset_dividend_asset_exdate_type",
        "asset_dividends",
        type_="unique",
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_asset_dividend_economic_identity
        ON asset_dividends (
            asset_id,
            ex_date,
            dividend_type,
            COALESCE(payment_date, ex_date)
        )
        """
    )


def downgrade() -> None:
    op.drop_index(
        "uq_asset_dividend_economic_identity",
        table_name="asset_dividends",
    )
    op.create_unique_constraint(
        "uq_asset_dividend_asset_exdate_type",
        "asset_dividends",
        ["asset_id", "ex_date", "dividend_type"],
    )
