"""add portfolio-scoped fixed-income contract metadata

Revision ID: 20261017_fixed_income_contracts
Revises: 20261016_corp_ev_effective_date
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261017_fixed_income_contracts"
down_revision: str | None = "20261016_corp_ev_effective_date"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PRODUCT_TYPES = (
    "CDB", "RDB", "LCI", "LCA", "LC", "LIG", "CRI", "CRA",
    "DEBENTURE", "DEBENTURE_INCENTIVADA", "LETRA_FINANCEIRA", "OUTRO",
)
_RATE_UNITS = (
    "PERCENT_OF_INDEXER", "ANNUAL_PERCENT", "ANNUAL_SPREAD_PERCENT",
)
_LIQUIDITY_TYPES = ("DAILY", "AT_MATURITY", "CONTRACTUAL", "UNKNOWN")


def upgrade() -> None:
    op.create_table(
        "fixed_income_contracts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("product_type", sa.String(length=64), nullable=False),
        sa.Column("issuer", sa.String(length=150), nullable=True),
        sa.Column("indexer", sa.String(length=64), nullable=True),
        sa.Column("rate_value", sa.Numeric(18, 8), nullable=True),
        sa.Column("rate_unit", sa.String(length=32), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("liquidity_type", sa.String(length=32), nullable=True),
        sa.Column("grace_period_end", sa.Date(), nullable=True),
        sa.Column("tax_exempt", sa.Boolean(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"],
            name="fk_fixed_income_contracts_portfolio",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "portfolio_id", "id",
            name="uq_fixed_income_contract_portfolio_id",
        ),
        sa.CheckConstraint(
            "product_type IN ("
            + ", ".join(f"'{value}'" for value in _PRODUCT_TYPES)
            + ")",
            name="ck_fixed_income_contract_product_type",
        ),
        sa.CheckConstraint(
            "rate_unit IS NULL OR rate_unit IN ("
            + ", ".join(f"'{value}'" for value in _RATE_UNITS) + ")",
            name="ck_fixed_income_contract_rate_unit",
        ),
        sa.CheckConstraint(
            "(rate_value IS NULL AND rate_unit IS NULL) OR "
            "(rate_value IS NOT NULL AND rate_unit IS NOT NULL)",
            name="ck_fixed_income_contract_rate_pair",
        ),
        sa.CheckConstraint(
            "liquidity_type IS NULL OR liquidity_type IN ("
            + ", ".join(f"'{value}'" for value in _LIQUIDITY_TYPES)
            + ")",
            name="ck_fixed_income_contract_liquidity_type",
        ),
    )
    op.create_index(
        "ix_fixed_income_contracts_portfolio_id",
        "fixed_income_contracts",
        ["portfolio_id"],
    )
    op.add_column(
        "transactions",
        sa.Column("fixed_income_contract_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_transactions_fixed_income_contract_id",
        "transactions",
        ["fixed_income_contract_id"],
    )
    op.create_foreign_key(
        "fk_transactions_fixed_income_contract_portfolio",
        "transactions",
        "fixed_income_contracts",
        ["portfolio_id", "fixed_income_contract_id"],
        ["portfolio_id", "id"],
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    bind = op.get_bind()
    linked_transactions = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM transactions "
            "WHERE fixed_income_contract_id IS NOT NULL"
        )
    ).scalar_one()
    contracts = bind.execute(
        sa.text("SELECT COUNT(*) FROM fixed_income_contracts")
    ).scalar_one()
    if linked_transactions or contracts:
        raise RuntimeError(
            "cannot downgrade while fixed-income contracts or links exist"
        )

    op.drop_constraint(
        "fk_transactions_fixed_income_contract_portfolio",
        "transactions",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_transactions_fixed_income_contract_id", table_name="transactions"
    )
    op.drop_column("transactions", "fixed_income_contract_id")
    op.drop_index(
        "ix_fixed_income_contracts_portfolio_id",
        table_name="fixed_income_contracts",
    )
    op.drop_table("fixed_income_contracts")
