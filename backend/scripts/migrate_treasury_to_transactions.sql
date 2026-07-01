-- =============================================================================
-- MIGRATE treasury_investments -> transactions
-- =============================================================================
-- Execute BEFORE: alembic upgrade 023
--
-- O que este script faz:
--   1. Verifica se ja existem transacoes duplicadas (seguranca)
--   2. Insere cada linha de treasury_investments como uma transacao 'buy'
--      com asset_type = 'tesouro_direto'
--   3. Preserva: portfolio_id, brapi_name (ticker), quantity, purchase_price,
--      date_purchase, treasury_type e rate_at_purchase (em notes)
--
-- Campos mapeados:
--   treasury_investments.brapi_name        -> transactions.ticker
--   treasury_investments.purchase_price    -> transactions.price
--   treasury_investments.quantity          -> transactions.quantity
--   treasury_investments.date_purchase     -> transactions.date
--   treasury_investments.portfolio_id      -> transactions.portfolio_id
--   treasury_investments.treasury_type     -> transactions.notes (parte)
--   treasury_investments.rate_at_purchase  -> transactions.notes (parte)
-- =============================================================================

BEGIN;

-- Seguranca: lista possiveis duplicatas antes de inserir
-- (execute este SELECT manualmente para conferir antes de rodar o script completo)
-- SELECT t.brapi_name, t.date_purchase, t.portfolio_id
-- FROM treasury_investments t
-- INNER JOIN transactions tx
--   ON tx.portfolio_id = t.portfolio_id
--   AND tx.ticker = t.brapi_name
--   AND tx.date = t.date_purchase
--   AND tx.asset_type = 'tesouro_direto';

-- Insercao principal
INSERT INTO transactions (
    portfolio_id,
    ticker,
    asset_type,
    operation,
    quantity,
    price,
    fees,
    date,
    currency,
    notes
)
SELECT
    ti.portfolio_id,
    ti.brapi_name                                                  AS ticker,
    'tesouro_direto'                                               AS asset_type,
    'buy'                                                          AS operation,
    ti.quantity,
    ti.purchase_price                                              AS price,
    0.0                                                            AS fees,
    ti.date_purchase                                               AS date,
    'BRL'                                                          AS currency,
    CONCAT(
        'Migrado de treasury_investments | ',
        'Tipo: ', COALESCE(ti.treasury_type::text, 'N/A'), ' | ',
        'Taxa na compra: ', COALESCE(ti.rate_at_purchase::text, 'N/A'), '%'
    )                                                              AS notes
FROM treasury_investments ti
WHERE ti.is_active = true  -- migra apenas os ativos; ajuste se quiser migrar todos
ON CONFLICT DO NOTHING;

-- Relatorio pos-insercao
SELECT
    COUNT(*) AS registros_migrados,
    SUM(quantity * price) AS valor_total_migrado
FROM transactions
WHERE asset_type = 'tesouro_direto'
  AND notes LIKE 'Migrado de treasury_investments%';

COMMIT;

-- =============================================================================
-- PROXIMOS PASSOS apos confirmar a migracao:
--   alembic upgrade 023
-- =============================================================================
