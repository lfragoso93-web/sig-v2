"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # --- system_configs ---
    op.create_table(
        'system_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_system_configs_key', 'system_configs', ['key'], unique=True)

    # --- assets ---
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(20), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('asset_type', sa.String(50), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='BRL'),
        sa.Column('brapi_ticker', sa.String(20), nullable=True),
        sa.Column('sector', sa.String(100), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_assets_id', 'assets', ['id'])
    op.create_index('ix_assets_ticker', 'assets', ['ticker'])
    op.create_unique_constraint('uq_assets_ticker_type', 'assets', ['ticker', 'asset_type'])

    # --- portfolios ---
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_portfolios_id', 'portfolios', ['id'])
    op.create_index('ix_portfolios_user_id', 'portfolios', ['user_id'])

    # --- transactions ---
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 8), nullable=False),
        sa.Column('unit_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('total_cost', sa.Numeric(18, 4), nullable=False),
        sa.Column('fees', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('broker', sa.String(100), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('is_day_trade', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'])
    op.create_index('ix_transactions_portfolio_id', 'transactions', ['portfolio_id'])
    op.create_index('ix_transactions_asset_id', 'transactions', ['asset_id'])
    op.create_index('ix_transactions_date', 'transactions', ['date'])

    # --- portfolio_positions ---
    op.create_table(
        'portfolio_positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('average_price', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('total_invested', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('realized_profit', sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('portfolio_id', 'asset_id', name='uq_position_portfolio_asset'),
    )
    op.create_index('ix_portfolio_positions_id', 'portfolio_positions', ['id'])

    # --- dividends ---
    op.create_table(
        'dividends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('dividend_type', sa.String(50), nullable=False),
        sa.Column('ex_date', sa.Date(), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('value_per_unit', sa.Numeric(18, 8), nullable=False),
        sa.Column('quantity_held', sa.Numeric(18, 8), nullable=False),
        sa.Column('total_value', sa.Numeric(18, 4), nullable=False),
        sa.Column('is_automatic', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('brapi_event_id', sa.String(150), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('brapi_event_id', name='uq_dividend_brapi_event_id'),
    )
    op.create_index('ix_dividends_id', 'dividends', ['id'])
    op.create_index('ix_dividends_ex_date', 'dividends', ['ex_date'])

    # --- corporate_events ---
    op.create_table(
        'corporate_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDENTE'),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('ratio', sa.Numeric(18, 8), nullable=False),
        sa.Column('brapi_event_id', sa.String(150), nullable=True),
        sa.Column('raw_data', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('brapi_event_id', name='uq_corporate_event_brapi_id'),
    )
    op.create_index('ix_corporate_events_id', 'corporate_events', ['id'])
    op.create_index('ix_corporate_events_status', 'corporate_events', ['status'])

    # --- seed: system_configs default ---
    op.execute("""
        INSERT INTO system_configs (key, value, description, is_public) VALUES
        ('allow_registration', 'true', 'Permite novos cadastros publicos', true),
        ('max_portfolios_per_user', '10', 'Limite de carteiras por usuario', false),
        ('app_name', 'SIG v2', 'Nome do sistema', true),
        ('maintenance_mode', 'false', 'Modo de manutencao', true)
    """)


def downgrade() -> None:
    op.drop_table('corporate_events')
    op.drop_table('dividends')
    op.drop_table('portfolio_positions')
    op.drop_table('transactions')
    op.drop_table('portfolios')
    op.drop_table('assets')
    op.drop_table('system_configs')
    op.drop_table('users')
