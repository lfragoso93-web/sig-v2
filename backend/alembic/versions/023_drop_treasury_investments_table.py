"""
drop treasury_investments table

Revision ID: 023
Revises: 022
Create Date: 2026-07-01

Tesouro Direto positions agora sao derivadas diretamente da tabela
transactions (asset_type = 'tesouro_direto'). A tabela
treasury_investments nao e mais utilizada.

O downgrade recria a tabela para que o rollback seja seguro.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("treasury_investments")


def downgrade() -> None:
    op.create_table(
        "treasury_investments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("brapi_name", sa.String(length=100), nullable=False),
        sa.Column("invested_value", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("purchase_price", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treasury_investments_id", "treasury_investments", ["id"], unique=False)
    op.create_index("ix_treasury_investments_portfolio_id", "treasury_investments", ["portfolio_id"], unique=False)
