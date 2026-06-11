-- Migração da tabela treasury_investments
-- Substitui o schema antigo (treasury_type, quantity, purchase_price, etc.)
-- pelo schema simplificado (invested_value, purchase_date, maturity_date)
--
-- Execute com:
--   docker compose exec db psql -U postgres -d sig_db -f /dev/stdin < backend/scripts/migrate_treasury.sql
-- OU diretamente:
--   docker compose exec -T db psql -U postgres -d sig_db < backend/scripts/migrate_treasury.sql

BEGIN;

-- 1. Remove a tabela antiga (não há dados úteis pois os campos não batiam)
DROP TABLE IF EXISTS treasury_investments CASCADE;

-- 2. Remove o enum antigo se existir (criado inline pelo FastAPI anterior)
DROP TYPE IF EXISTS treasurytype CASCADE;

-- 3. Recria a tabela com o novo schema simplificado
CREATE TABLE treasury_investments (
    id              SERIAL PRIMARY KEY,
    portfolio_id    INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    brapi_name      VARCHAR(100) NOT NULL,
    invested_value  NUMERIC(18, 2) NOT NULL,
    purchase_date   DATE NOT NULL,
    maturity_date   DATE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_treasury_investments_portfolio_id
    ON treasury_investments (portfolio_id);

COMMIT;

-- Verificação
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'treasury_investments'
ORDER BY ordinal_position;
