"""initial schema — cria todas as tabelas

Revision ID: 001
Down revision: None
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('email', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── assets ─────────────────────────────────────────────────────────────
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('ticker', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('asset_type', sa.String(50), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='BRL'),
        sa.Column('last_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('last_price_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('brapi_ticker', sa.String(50), nullable=True),
        sa.Column('sector', sa.String(100), nullable=True),
        sa.Column('sub_sector', sa.String(100), nullable=True),
        sa.Column('float_description', sa.Float(), nullable=True),
    )

    # ── portfolios ─────────────────────────────────────────────────────────
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── transactions ───────────────────────────────────────────────────────
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ticker', sa.String(100), nullable=False, index=True),
        sa.Column('asset_type', sa.String(50), nullable=False),
        sa.Column('operation', sa.String(10), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('fees', sa.Float(), nullable=False, server_default='0'),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('currency', sa.String(10), nullable=False, server_default='BRL'),
        sa.Column('fx_rate', sa.Numeric(18, 8), nullable=True),
        sa.Column('price_brl', sa.Numeric(18, 8), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
    )

    # ── portfolio_positions ────────────────────────────────────────────────
    op.create_table(
        'portfolio_positions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='RESTRICT'), nullable=False, index=True),
        sa.Column('quantity', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('average_price', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('total_invested', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('realized_profit', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('portfolio_id', 'asset_id', name='uq_position_portfolio_asset'),
    )

    # ── asset_prices ───────────────────────────────────────────────────────
    op.create_table(
        'asset_prices',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('open', sa.Numeric(18, 8), nullable=True),
        sa.Column('high', sa.Numeric(18, 8), nullable=True),
        sa.Column('low', sa.Numeric(18, 8), nullable=True),
        sa.Column('close', sa.Numeric(18, 8), nullable=False),
        sa.Column('volume', sa.Numeric(24, 2), nullable=True),
        sa.Column('source', sa.String(30), nullable=False, server_default='brapi'),
        sa.UniqueConstraint('asset_id', 'timestamp', name='uq_price_asset_timestamp'),
    )

    # ── asset_dividends ────────────────────────────────────────────────────
    op.create_table(
        'asset_dividends',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('ex_date', sa.Date(), nullable=False, index=True),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('dividend_type', sa.String(30), nullable=False, server_default='DIVIDENDO'),
        sa.Column('value_per_unit', sa.Numeric(18, 8), nullable=False),
        sa.Column('source', sa.String(30), nullable=False, server_default='brapi'),
        sa.UniqueConstraint('asset_id', 'ex_date', 'dividend_type', name='uq_asset_dividend_asset_exdate_type'),
    )

    # ── dividends ──────────────────────────────────────────────────────────
    op.create_table(
        'dividends',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('asset_dividend_id', sa.Integer(), sa.ForeignKey('asset_dividends.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('quantity', sa.Numeric(20, 8), nullable=True),
        sa.Column('total_value', sa.Numeric(20, 8), nullable=True),
        sa.Column('net_value', sa.Numeric(20, 8), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='RECEBIDO'),
        sa.Column('ticker', sa.String(50), nullable=True, index=True),
        sa.Column('ex_date', sa.Date(), nullable=True),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('value_per_unit', sa.Numeric(20, 8), nullable=True),
        sa.Column('total_received', sa.Numeric(20, 8), nullable=True),
        sa.Column('dividend_type', sa.String(30), nullable=True),
    )

    # ── fixed_income_investments ───────────────────────────────────────────
    op.create_table(
        'fixed_income_investments',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('institution', sa.String(150), nullable=False),
        sa.Column('fixed_income_type', sa.String(30), nullable=False),
        sa.Column('indexer', sa.String(30), nullable=False),
        sa.Column('rate', sa.Numeric(10, 4), nullable=False),
        sa.Column('invested_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('date_start', sa.Date(), nullable=False),
        sa.Column('date_maturity', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_ir_exempt', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── treasury_investments ───────────────────────────────────────────────
    op.create_table(
        'treasury_investments',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('brapi_name', sa.String(100), nullable=False),
        sa.Column('invested_value', sa.Numeric(18, 2), nullable=False),
        sa.Column('purchase_date', sa.Date(), nullable=False),
        sa.Column('maturity_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── goals ──────────────────────────────────────────────────────────────
    op.create_table(
        'goals',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('target_value', sa.Float(), nullable=False),
        sa.Column('current_value', sa.Float(), nullable=False, server_default='0'),
        sa.Column('target_date', sa.DateTime(), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # ── irpf_reports ───────────────────────────────────────────────────────
    op.create_table(
        'irpf_reports',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('data', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # ── corporate_events ───────────────────────────────────────────────────
    op.create_table(
        'corporate_events',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id'), nullable=False, index=True),
        sa.Column('ticker', sa.String(50), nullable=False, index=True),
        sa.Column('event_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDENTE'),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('ratio', sa.Numeric(20, 8), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('brapi_event_id', sa.String(100), unique=True, nullable=True),
        sa.Column('raw_data', sa.String(), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id'), nullable=True),
    )

    # ── system_configs ─────────────────────────────────────────────────────
    op.create_table(
        'system_configs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('key', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── portfolio_snapshots ────────────────────────────────────────────────
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('snapshot_date', sa.Date(), nullable=False, index=True),
        sa.Column('market_value', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('cost_basis', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('invested_total', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('realized_pnl', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('unrealized_pnl', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('total_pnl', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('return_pct', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('portfolio_id', 'snapshot_date', name='uq_snapshot_portfolio_date'),
    )


def downgrade():
    op.drop_table('portfolio_snapshots')
    op.drop_table('system_configs')
    op.drop_table('corporate_events')
    op.drop_table('irpf_reports')
    op.drop_table('goals')
    op.drop_table('treasury_investments')
    op.drop_table('fixed_income_investments')
    op.drop_table('dividends')
    op.drop_table('asset_dividends')
    op.drop_table('asset_prices')
    op.drop_table('portfolio_positions')
    op.drop_table('transactions')
    op.drop_table('portfolios')
    op.drop_table('assets')
    op.drop_table('users')
