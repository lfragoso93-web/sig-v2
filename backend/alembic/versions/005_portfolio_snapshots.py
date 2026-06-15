"""Cria tabela portfolio_snapshots para evolução patrimonial diária.

Revision ID: 005_portfolio_snapshots
Revises: 004_add_last_price_to_assets
Create Date: 2026-06-15

Motivação:
  Persistir o valor de mercado diário de cada carteira, calculado com base
  nos preços de fechamento de asset_prices.

  Permite:
    - Gráfico de evolução patrimonial diária e mensal.
    - Cálculo de rentabilidade em qualquer janela sem recalcular transações.
    - Base para TWR (Time-Weighted Return) e outras métricas de performance.

  Um registro por carteira por dia (INSERT ON CONFLICT DO UPDATE).
  Rollback remove a tabela completamente (dados reconstituíveis via scheduler).
"""
from alembic import op
import sqlalchemy as sa

revision = '005_portfolio_snapshots'
down_revision = '004_add_last_price_to_assets'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id',             sa.Integer(),       primary_key=True),
        sa.Column('portfolio_id',   sa.Integer(),       nullable=False),
        sa.Column('snapshot_date',  sa.Date(),          nullable=False,
                  comment='Data do fechamento (dia útil ou último dado disponível).'),

        # Valores principais
        sa.Column('market_value',   sa.Numeric(18, 2),  nullable=False, server_default='0',
                  comment='Valor total de mercado na data (Σ qty × close_price).'),
        sa.Column('cost_basis',     sa.Numeric(18, 2),  nullable=False, server_default='0',
                  comment='Custo total das posições abertas (Σ qty × avg_price).'),
        sa.Column('invested_total', sa.Numeric(18, 2),  nullable=False, server_default='0',
                  comment='Total aportado líquido acumulado até a data.'),

        # PnL
        sa.Column('realized_pnl',   sa.Numeric(18, 2),  nullable=False, server_default='0',
                  comment='Lucro/prejuízo realizado acumulado até a data.'),
        sa.Column('unrealized_pnl', sa.Numeric(18, 2),  nullable=False, server_default='0',
                  comment='market_value - cost_basis.'),
        sa.Column('total_pnl',      sa.Numeric(18, 2),  nullable=False, server_default='0',
                  comment='realized_pnl + unrealized_pnl.'),
        sa.Column('return_pct',     sa.Numeric(10, 4),  nullable=False, server_default='0',
                  comment='total_pnl / invested_total × 100.'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  onupdate=sa.func.now()),

        # Constraints
        sa.ForeignKeyConstraint(
            ['portfolio_id'], ['portfolios.id'],
            ondelete='CASCADE',
        ),
        sa.UniqueConstraint('portfolio_id', 'snapshot_date',
                            name='uq_snapshot_portfolio_date'),
    )

    # Índices para queries de evolução (por carteira no tempo)
    op.create_index('ix_portfolio_snapshots_portfolio_id',
                    'portfolio_snapshots', ['portfolio_id'])
    op.create_index('ix_portfolio_snapshots_snapshot_date',
                    'portfolio_snapshots', ['snapshot_date'])
    # Índice composto: leitura de série temporal por carteira
    op.create_index('ix_portfolio_snapshots_portfolio_date',
                    'portfolio_snapshots', ['portfolio_id', 'snapshot_date'])


def downgrade() -> None:
    op.drop_index('ix_portfolio_snapshots_portfolio_date',
                  table_name='portfolio_snapshots')
    op.drop_index('ix_portfolio_snapshots_snapshot_date',
                  table_name='portfolio_snapshots')
    op.drop_index('ix_portfolio_snapshots_portfolio_id',
                  table_name='portfolio_snapshots')
    op.drop_table('portfolio_snapshots')
