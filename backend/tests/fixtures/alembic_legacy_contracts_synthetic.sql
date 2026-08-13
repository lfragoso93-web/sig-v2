\set ON_ERROR_STOP on

BEGIN;

-- Fixture sintética exclusiva para PostgreSQL descartável.
-- Nenhuma linha deve sobreviver: o arquivo termina obrigatoriamente em ROLLBACK.

INSERT INTO users (
    name,
    email,
    hashed_password,
    role,
    is_active
)
VALUES (
    'Fixture Alembic Legacy',
    'fixture-alembic-legacy@invalid.local',
    'not-a-real-password-hash',
    'user',
    true
)
RETURNING id \gset fixture_user_

INSERT INTO portfolios (
    user_id,
    name,
    description,
    is_active
)
VALUES (
    :fixture_user_id,
    'Fixture Alembic Legacy',
    'Carteira sintética para validar contratos legados',
    true
)
RETURNING id \gset fixture_portfolio_

INSERT INTO goals (
    portfolio_id,
    name,
    goal_type,
    target_value,
    description,
    is_active
)
VALUES (
    :fixture_portfolio_id,
    'Fixture Goal Allocation',
    'ALOCACAO',
    1000.00,
    'Meta sintética para validar FK de goal_allocations',
    true
)
RETURNING id \gset fixture_goal_

INSERT INTO irpf_records (
    user_id,
    year,
    month,
    market,
    gross_profit,
    loss_offset,
    taxable_profit,
    ir_rate,
    ir_due,
    ir_withheld,
    ir_to_pay,
    is_exempt,
    darf_code
)
VALUES (
    :fixture_user_id,
    2026,
    1,
    'ACOES',
    100.00,
    10.00,
    90.00,
    0.1500,
    13.50,
    1.00,
    12.50,
    false,
    '6015'
);

INSERT INTO irpf_losses (
    user_id,
    market,
    year,
    month,
    accumulated_loss
)
VALUES (
    :fixture_user_id,
    'ACOES',
    2026,
    1,
    10.00
);

INSERT INTO goal_allocations (
    goal_id,
    asset_type,
    target_percentage
)
VALUES (
    :fixture_goal_id,
    'ACAO',
    50.000
);

-- Cada SELECT falha por divisão por zero se a fixture não produzir exatamente uma linha.
SELECT 1 / CASE WHEN COUNT(*) = 1 THEN 1 ELSE 0 END
FROM irpf_records
WHERE user_id = :fixture_user_id;

SELECT 1 / CASE WHEN COUNT(*) = 1 THEN 1 ELSE 0 END
FROM irpf_losses
WHERE user_id = :fixture_user_id;

SELECT 1 / CASE WHEN COUNT(*) = 1 THEN 1 ELSE 0 END
FROM goal_allocations
WHERE goal_id = :fixture_goal_id;

ROLLBACK;
