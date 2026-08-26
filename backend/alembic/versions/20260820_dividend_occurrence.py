"""expand asset dividend occurrence identity

Revision ID: 20260820_dividend_occurrence
Revises: 20260813_rate_history_metadata

Eventos monetarios distintos podem compartilhar ativo, Data Ex, tipo e data de
pagamento. O valor por unidade, na precisao fisica NUMERIC(18, 8), passa a
compor a identidade persistida para que essas ocorrencias nao sejam colapsadas.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260820_dividend_occurrence"
down_revision: str = "20260813_rate_history_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(
        "uq_asset_dividend_economic_identity",
        table_name="asset_dividends",
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_asset_dividend_economic_identity
        ON asset_dividends (
            asset_id,
            ex_date,
            dividend_type,
            COALESCE(payment_date, ex_date),
            value_per_unit
        )
        """
    )


def downgrade() -> None:
    op.drop_index(
        "uq_asset_dividend_economic_identity",
        table_name="asset_dividends",
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
