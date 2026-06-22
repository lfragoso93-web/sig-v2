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


def _create_enum_if_not_exists(name: str, values: list) -> None:
    """Cria um ENUM de forma idempotente no PostgreSQL."""
    values_sql = ", ".join(f"'{v}'" for v in values)
    op.execute(f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN
                CREATE TYPE {name} AS ENUM ({values_sql});
            END IF;
        END $$;
    """)


def upgrade() -> None:
    # Cria ENUMs de forma idempotente
    _create_enum_if_not_exists('userrole', ['user', 'superadmin'])
    _create_enum_if_not_exists('assettype', ['ACAO', 'FII', 'ETF_NACIONAL', 'TESOURO_DIRETO', 'STOCK', 'ETF_INTERNACIONAL', 'CRIPTO', 'RENDA_FIXA'])
    _create_enum_if_not_exists('assetcurrency', ['BRL', 'USD', 'EUR', 'BTC'])
    _create_enum_if_not_exists('transactiontype', ['COMPRA', 'VENDA', 'DESDOBRAMENTO', 'GRUPAMENTO', 'BONIFICACAO', 'TRANSFERENCIA_ENTRADA', 'TRANSFERENCIA_SAIDA'])
    _create_enum_if_not_exists('dividendtype', ['DIVIDENDO', 'JCP', 'RENDIMENTO', 'AMORTIZACAO', 'FRACAO', 'OUTROS'])
    _create_enum_if_not_exists('fixedincometype', ['CDB', 'LCI', 'LCA', 'LCI_LCA', 'CRI', 'CRA', 'DEBENTURE', 'POUPANCA', 'OUTROS'])
    _create_enum_if_not_exists('indexertype', ['CDI', 'IPCA_PLUS', 'SELIC', 'PREFIXADO', 'IGPM_PLUS'])
    _create_enum_if_not_exists('treasurytype', ['Tesouro Selic', 'Tesouro Prefixado', 'Tesouro Prefixado com Juros Semestrais', 'Tesouro IPCA+', 'Tesouro IPCA+ com Juros Semestrais', 'Tesouro IGP-M+ com Juros Semestrais', 'Tesouro Renda+', 'Tesouro Educa+'])
    _create_enum_if_not_exists('irpfmarket', ['ACOES', 'DAY_TRADE', 'FII', 'ETF', 'CRIPTO', 'RENDA_FIXA', 'STOCKS'])
    _create_enum_if_not_exists('goaltype', ['PATRIMONIO_ALVO', 'ALOCACAO', 'DY_MENSAL', 'RENTABILIDADE', 'APORTE_MENSAL'])

    # === USERS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            email VARCHAR(255) NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role userrole NOT NULL DEFAULT 'user',
            is_active BOOLEAN NOT NULL DEFAULT true,
            avatar_url VARCHAR(500),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)")

    # === PORTFOLIOS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(150) NOT NULL,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_portfolios_id ON portfolios (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_portfolios_user_id ON portfolios (user_id)")

    # === ASSETS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(30) NOT NULL,
            name VARCHAR(200) NOT NULL,
            asset_type assettype NOT NULL,
            currency assetcurrency NOT NULL DEFAULT 'BRL',
            brapi_ticker VARCHAR(50),
            sector VARCHAR(100),
            logo_url VARCHAR(500),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_asset_ticker_type UNIQUE (ticker, asset_type)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_assets_id ON assets (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_assets_ticker ON assets (ticker)")

    # === TRANSACTIONS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
            transaction_type transactiontype NOT NULL,
            date DATE NOT NULL,
            quantity NUMERIC(18,8) NOT NULL,
            unit_price NUMERIC(18,8) NOT NULL,
            total_cost NUMERIC(18,2) NOT NULL,
            fees NUMERIC(18,2) NOT NULL DEFAULT 0,
            broker VARCHAR(100),
            notes TEXT,
            is_day_trade BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_transactions_id ON transactions (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_transactions_portfolio_id ON transactions (portfolio_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_transactions_asset_id ON transactions (asset_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_transactions_date ON transactions (date)")

    # === PORTFOLIO POSITIONS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_positions (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
            quantity NUMERIC(18,8) NOT NULL DEFAULT 0,
            average_price NUMERIC(18,8) NOT NULL DEFAULT 0,
            total_invested NUMERIC(18,2) NOT NULL DEFAULT 0,
            realized_profit NUMERIC(18,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_position_portfolio_asset UNIQUE (portfolio_id, asset_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_portfolio_positions_id ON portfolio_positions (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_portfolio_positions_portfolio_id ON portfolio_positions (portfolio_id)")

    # === DIVIDENDS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS dividends (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
            dividend_type dividendtype NOT NULL,
            date_ex DATE NOT NULL,
            date_payment DATE,
            quantity_on_date NUMERIC(18,8) NOT NULL,
            value_per_share NUMERIC(18,8) NOT NULL,
            total_value NUMERIC(18,2) NOT NULL,
            is_projected BOOLEAN NOT NULL DEFAULT false,
            ir_withheld NUMERIC(18,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dividends_id ON dividends (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_dividends_portfolio_id ON dividends (portfolio_id)")

    # === FIXED INCOME ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS fixed_income_investments (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            institution VARCHAR(150) NOT NULL,
            fixed_income_type fixedincometype NOT NULL,
            indexer indexertype NOT NULL,
            rate NUMERIC(10,4) NOT NULL,
            invested_amount NUMERIC(18,2) NOT NULL,
            date_start DATE NOT NULL,
            date_maturity DATE,
            is_active BOOLEAN NOT NULL DEFAULT true,
            is_ir_exempt BOOLEAN NOT NULL DEFAULT false,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_fixed_income_investments_id ON fixed_income_investments (id)")

    # === TREASURY ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS treasury_investments (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            treasury_type treasurytype NOT NULL,
            brapi_name VARCHAR(100) NOT NULL,
            date_purchase DATE NOT NULL,
            date_maturity DATE NOT NULL,
            quantity NUMERIC(18,8) NOT NULL,
            purchase_price NUMERIC(18,6) NOT NULL,
            invested_amount NUMERIC(18,2) NOT NULL,
            rate_at_purchase NUMERIC(10,4) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            spread_rate NUMERIC(10,4),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_treasury_investments_id ON treasury_investments (id)")

    # === ASSET PRICES ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS asset_prices (
            id SERIAL PRIMARY KEY,
            asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
            timestamp TIMESTAMPTZ NOT NULL,
            open NUMERIC(18,8),
            high NUMERIC(18,8),
            low NUMERIC(18,8),
            close NUMERIC(18,8) NOT NULL,
            volume NUMERIC(24,2),
            source VARCHAR(30) NOT NULL DEFAULT 'brapi',
            CONSTRAINT uq_price_asset_timestamp UNIQUE (asset_id, timestamp)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_asset_prices_id ON asset_prices (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_asset_prices_asset_id ON asset_prices (asset_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_asset_prices_timestamp ON asset_prices (timestamp)")

    # === IRPF RECORDS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS irpf_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            market irpfmarket NOT NULL,
            gross_profit NUMERIC(18,2) NOT NULL DEFAULT 0,
            loss_offset NUMERIC(18,2) NOT NULL DEFAULT 0,
            taxable_profit NUMERIC(18,2) NOT NULL DEFAULT 0,
            ir_rate NUMERIC(6,4) NOT NULL DEFAULT 0,
            ir_due NUMERIC(18,2) NOT NULL DEFAULT 0,
            ir_withheld NUMERIC(18,2) NOT NULL DEFAULT 0,
            ir_to_pay NUMERIC(18,2) NOT NULL DEFAULT 0,
            is_exempt BOOLEAN NOT NULL DEFAULT false,
            darf_code VARCHAR(10),
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_irpf_records_id ON irpf_records (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_irpf_records_user_id ON irpf_records (user_id)")

    # === IRPF LOSSES ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS irpf_losses (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            market irpfmarket NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            accumulated_loss NUMERIC(18,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_irpf_losses_id ON irpf_losses (id)")

    # === GOALS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            name VARCHAR(150) NOT NULL,
            goal_type goaltype NOT NULL,
            target_value NUMERIC(18,2) NOT NULL,
            target_date DATE,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_goals_id ON goals (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_goals_portfolio_id ON goals (portfolio_id)")

    # === GOAL ALLOCATIONS ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS goal_allocations (
            id SERIAL PRIMARY KEY,
            goal_id INTEGER NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
            asset_type VARCHAR(30) NOT NULL,
            target_percentage NUMERIC(6,3) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_goal_allocations_id ON goal_allocations (id)")

    # === SYSTEM CONFIG ===
    op.execute("""
        CREATE TABLE IF NOT EXISTS system_configs (
            id SERIAL PRIMARY KEY,
            key VARCHAR(100) NOT NULL,
            value TEXT NOT NULL,
            description TEXT,
            is_public BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_system_configs_id ON system_configs (id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_system_configs_key ON system_configs (key)")

    # === SEED: configurações padrão (ignora se já existir) ===
    op.execute("""
        INSERT INTO system_configs (key, value, description, is_public)
        VALUES
            ('app_name', 'SGI', 'Nome do sistema', true),
            ('app_tagline', 'Sistema de Gestão de Investimentos', 'Subtítulo do sistema', true),
            ('allow_registration', 'true', 'Permite auto-registro de novos usuários', true),
            ('max_portfolios_per_user', '10', 'Limite de carteiras por usuário', false),
            ('ai_analysis_enabled', 'true', 'Habilita análise com IA (Gemini)', false),
            ('maintenance_mode', 'false', 'Modo manutenção — bloqueia acesso de usuários', true)
        ON CONFLICT (key) DO NOTHING
    """)


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS system_configs')
    op.execute('DROP TABLE IF EXISTS goal_allocations')
    op.execute('DROP TABLE IF EXISTS goals')
    op.execute('DROP TABLE IF EXISTS irpf_losses')
    op.execute('DROP TABLE IF EXISTS irpf_records')
    op.execute('DROP TABLE IF EXISTS asset_prices')
    op.execute('DROP TABLE IF EXISTS treasury_investments')
    op.execute('DROP TABLE IF EXISTS fixed_income_investments')
    op.execute('DROP TABLE IF EXISTS dividends')
    op.execute('DROP TABLE IF EXISTS portfolio_positions')
    op.execute('DROP TABLE IF EXISTS transactions')
    op.execute('DROP TABLE IF EXISTS assets')
    op.execute('DROP TABLE IF EXISTS portfolios')
    op.execute('DROP TABLE IF EXISTS users')
    for enum_name in ['userrole','assettype','assetcurrency','transactiontype',
                      'dividendtype','fixedincometype','indexertype','treasurytype',
                      'irpfmarket','goaltype']:
        op.execute(f'DROP TYPE IF EXISTS {enum_name}')
