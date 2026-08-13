"""align rate_history metadata with canonical benchmark contract

Revision ID: 20260813_rate_history_metadata
Revises: 20260811_asset_univ_source64
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260813_rate_history_metadata"
down_revision: str = "20260811_asset_univ_source64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INDICATOR_COMMENT = "Indicador: CDI | SELIC | IPCA | IGPM"
_SOURCE_COMMENT = (
    "Fonte da observacao persistida; canonicamente BCB_SGS para benchmarks"
)
_LEGACY_INDICATOR_COMMENT = "Indicador: CDI | IPCA | SELIC"
_LEGACY_SOURCE_COMMENT = "Fonte: BCB | BRAPI |SEED | MANUAL"


def upgrade() -> None:
    op.execute(
        "COMMENT ON COLUMN rate_history.indicator IS "
        f"'{_INDICATOR_COMMENT}'"
    )
    op.execute(
        "COMMENT ON COLUMN rate_history.source IS "
        f"'{_SOURCE_COMMENT}'"
    )


def downgrade() -> None:
    op.execute(
        "COMMENT ON COLUMN rate_history.indicator IS "
        f"'{_LEGACY_INDICATOR_COMMENT}'"
    )
    op.execute(
        "COMMENT ON COLUMN rate_history.source IS "
        f"'{_LEGACY_SOURCE_COMMENT}'"
    )
