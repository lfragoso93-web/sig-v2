"""Initial schema — SGI v2

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === USERS ===
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('user', 'superadmin', name='userrole'), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # === PORTFOLIOS ===
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_portfolios_id', 'portfolios', ['id'])
    op.create_index('ix_portfolios_user_id', 'portfolios', ['user_id'])

    # === ASSETS ===
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(30), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('asset_type', sa.Enum(
            'ACAO','FII','ETF_NACIONAL','TESOURO_DIRETO','STOCK',
            'ETF_INTERNACIONAL','CRIPTO','RENDA_FIXA', name='assettype'
        ), nullable=False),
        sa.Column('currency', sa.Enum('BRL','USD','EUR','BTC', name='assetcurrency'), nullable=False, server_default='BRL'),
        sa.Column('brapi_ticker', sa.String(50), nullable=True),
        sa.Column('sector', sa.String(100), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker', 'asset_type', name='uq_asset_ticker_type'),
    )
    op.create_index('ix_assets_id', 'assets', ['id'])
    op.create_index('ix_assets_ticker', 'assets', ['ticker'])

    # === TRANSACTIONS ===
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('transaction_type', sa.Enum(
            'COMPRA','VENDA','DESDOBRAMENTO','GRUPAMENTO',
            'BONIFICACAO','TRANSFERENCIA_ENTRADA','TRANSFERENCIA_SAIDA',
            name='transactiontype'
        ), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 8), nullable=False),
        sa.Column('unit_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('total_cost', sa.Numeric(18, 2), nullable=False),
        sa.Column('fees', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('broker', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_day_trade', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'])
    op.create_index('ix_transactions_portfolio_id', 'transactions', ['portfolio_id'])
    op.create_index('ix_transactions_asset_id', 'transactions', ['asset_id'])
    op.create_index('ix_transactions_date', 'transactions', ['date'])

    # === PORTFOLIO POSITIONS ===
    op.create_table(
        'portfolio_positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('average_price', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('total_invested', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('realized_profit', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('portfolio_id', 'asset_id', name='uq_position_portfolio_asset'),
    )
    op.create_index('ix_portfolio_positions_id', 'portfolio_positions', ['id'])
    op.create_index('ix_portfolio_positions_portfolio_id', 'portfolio_positions', ['portfolio_id'])

    # === DIVIDENDS ===
    op.create_table(
        'dividends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('dividend_type', sa.Enum('DIVIDENDO','JCP','RENDIMENTO','AMORTIZACAO','FRACAO','OUTROS', name='dividendtype'), nullable=False),
        sa.Column('date_ex', sa.Date(), nullable=False),
        sa.Column('date_payment', sa.Date(), nullable=True),
        sa.Column('quantity_on_date', sa.Numeric(18, 8), nullable=False),
        sa.Column('value_per_share', sa.Numeric(18, 8), nullable=False),
        sa.Column('total_value', sa.Numeric(18, 2), nullable=False),
        sa.Column('is_projected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ir_withheld', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dividends_id', 'dividends', ['id'])
    op.create_index('ix_dividends_portfolio_id', 'dividends', ['portfolio_id'])

    # === FIXED INCOME ===
    op.create_table(
        'fixed_income_investments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('institution', sa.String(150), nullable=False),
        sa.Column('fixed_income_type', sa.Enum('CDB','LCI','LCA','LCI_LCA','CRI','CRA','DEBENTURE','POUPANCA','OUTROS', name='fixedincometype'), nullable=False),
        sa.Column('indexer', sa.Enum('CDI','IPCA_PLUS','SELIC','PREFIXADO','IGPM_PLUS', name='indexertype'), nullable=False),
        sa.Column('rate', sa.Numeric(10, 4), nullable=False),
        sa.Column('invested_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('date_start', sa.Date(), nullable=False),
        sa.Column('date_maturity', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_ir_exempt', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fixed_income_investments_id', 'fixed_income_investments', ['id'])

    # === TREASURY ===
    op.create_table(
        'treasury_investments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('treasury_type', sa.Enum(
            'Tesouro Selic','Tesouro Prefixado','Tesouro Prefixado com Juros Semestrais',
            'Tesouro IPCA+','Tesouro IPCA+ com Juros Semestrais',
            'Tesouro IGP-M+ com Juros Semestrais','Tesouro Renda+','Tesouro Educa+',
            name='treasurytype'
        ), nullable=False),
        sa.Column('brapi_name', sa.String(100), nullable=False),
        sa.Column('date_purchase', sa.Date(), nullable=False),
        sa.Column('date_maturity', sa.Date(), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 8), nullable=False),
        sa.Column('purchase_price', sa.Numeric(18, 6), nullable=False),
        sa.Column('invested_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('rate_at_purchase', sa.Numeric(10, 4), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('spread_rate', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_treasury_investments_id', 'treasury_investments', ['id'])

    # === ASSET PRICES ===
    op.create_table(
        'asset_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('open', sa.Numeric(18, 8), nullable=True),
        sa.Column('high', sa.Numeric(18, 8), nullable=True),
        sa.Column('low', sa.Numeric(18, 8), nullable=True),
        sa.Column('close', sa.Numeric(18, 8), nullable=False),
        sa.Column('volume', sa.Numeric(24, 2), nullable=True),
        sa.Column('source', sa.String(30), nullable=False, server_default='brapi'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_id', 'timestamp', name='uq_price_asset_timestamp'),
    )
    op.create_index('ix_asset_prices_id', 'asset_prices', ['id'])
    op.create_index('ix_asset_prices_asset_id', 'asset_prices', ['asset_id'])
    op.create_index('ix_asset_prices_timestamp', 'asset_prices', ['timestamp'])

    # === IRPF RECORDS ===
    op.create_table(
        'irpf_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('market', sa.Enum('ACOES','DAY_TRADE','FII','ETF','CRIPTO','RENDA_FIXA','STOCKS', name='irpfmarket'), nullable=False),
        sa.Column('gross_profit', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('loss_offset', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('taxable_profit', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('ir_rate', sa.Numeric(6, 4), nullable=False, server_default='0'),
        sa.Column('ir_due', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('ir_withheld', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('ir_to_pay', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('is_exempt', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('darf_code', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_irpf_records_id', 'irpf_records', ['id'])
    op.create_index('ix_irpf_records_user_id', 'irpf_records', ['user_id'])

    # === IRPF LOSSES ===
    op.create_table(
        'irpf_losses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('market', sa.Enum('ACOES','DAY_TRADE','FII','ETF','CRIPTO','RENDA_FIXA','STOCKS', name='irpfmarket'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('accumulated_loss', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_irpf_losses_id', 'irpf_losses', ['id'])

    # === GOALS ===
    op.create_table(
        'goals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('goal_type', sa.Enum('PATRIMONIO_ALVO','ALOCACAO','DY_MENSAL','RENTABILIDADE','APORTE_MENSAL', name='goaltype'), nullable=False),
        sa.Column('target_value', sa.Numeric(18, 2), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_goals_id', 'goals', ['id'])
    op.create_index('ix_goals_portfolio_id', 'goals', ['portfolio_id'])

    # === GOAL ALLOCATIONS ===
    op.create_table(
        'goal_allocations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('goal_id', sa.Integer(), sa.ForeignKey('goals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_type', sa.String(30), nullable=False),
        sa.Column('target_percentage', sa.Numeric(6, 3), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_goal_allocations_id', 'goal_allocations', ['id'])

    # === SYSTEM CONFIG ===
    op.create_table(
        'system_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_system_configs_id', 'system_configs', ['id'])
    op.create_index('ix_system_configs_key', 'system_configs', ['key'], unique=True)

    # === SEED: configurações padrão ===
    op.execute("""
        INSERT INTO system_configs (key, value, description, is_public) VALUES
        ('app_name', 'SGI', 'Nome do sistema', true),
        ('app_tagline', 'Sistema de Gestão de Investimentos', 'Subtítulo do sistema', true),
        ('allow_registration', 'true', 'Permite auto-registro de novos usuários', true),
        ('max_portfolios_per_user', '10', 'Limite de carteiras por usuário', false),
        ('ai_analysis_enabled', 'true', 'Habilita análise com IA (Gemini)', false),
        ('maintenance_mode', 'false', 'Modo manutenção — bloqueia acesso de usuários', true)
    """)


def downgrade() -> None:
    op.drop_table('system_configs')
    op.drop_table('goal_allocations')
    op.drop_table('goals')
    op.drop_table('irpf_losses')
    op.drop_table('irpf_records')
    op.drop_table('asset_prices')
    op.drop_table('treasury_investments')
    op.drop_table('fixed_income_investments')
    op.drop_table('dividends')
    op.drop_table('portfolio_positions')
    op.drop_table('transactions')
    op.drop_table('assets')
    op.drop_table('portfolios')
    op.drop_table('users')
    # Drop enums
    for enum_name in ['userrole','assettype','assetcurrency','transactiontype',
                      'dividendtype','fixedincometype','indexertype','treasurytype',
                      'irpfmarket','goaltype']:
        op.execute(f'DROP TYPE IF EXISTS {enum_name}')
