# Endurecimento de timestamps Alembic — agosto de 2026

## Contexto

A Issue #241 identificou deriva de nulabilidade entre o `TimestampMixin` ORM (`nullable=False`) e migrations históricas que criaram `created_at`/`updated_at` com `DEFAULT now()` porém sem `NOT NULL`.

Em 07/08/2026, a evidência PostgreSQL local confirmou zero linhas com timestamps nulos em:

- `users`;
- `portfolios`;
- `system_configs`;
- `fixed_income_investments`;
- `portfolio_positions`;
- `portfolio_snapshots`.

## Decisão arquitetural

O contrato canônico passa a preservar a invariável do `TimestampMixin`: timestamps de criação e atualização não podem ser nulos.

Não será feito backfill silencioso. Cada migration conta previamente as linhas incompatíveis e aborta com erro explícito se encontrar qualquer `NULL`.

## Cadeia de migrations

1. `20260807_users_portfolios_ts_nn`
   - `users.created_at`;
   - `users.updated_at`;
   - `portfolios.created_at`;
   - `portfolios.updated_at`.

2. `20260807_config_fixed_ts_nn`
   - `system_configs.created_at`;
   - `system_configs.updated_at`;
   - `fixed_income_investments.created_at`;
   - `fixed_income_investments.updated_at`.

3. `20260807_positions_snapshots_ts_nn`
   - `portfolio_positions.created_at`;
   - `portfolio_positions.updated_at`;
   - `portfolio_snapshots.created_at`;
   - `portfolio_snapshots.updated_at`.

Cada downgrade restaura `nullable=True`, sem remover defaults nem dados.

## Gates

`test_timestamp_not_null_contraction_migrations.py` protege:

- ordem linear da cadeia;
- presença das tabelas esperadas em cada bloco;
- verificação prévia de `NULL`;
- ausência de `UPDATE`, `DELETE`, `TRUNCATE` ou `DROP TABLE`;
- `nullable=False` no upgrade;
- `nullable=True` no downgrade.

## Evidência exigida antes da certificação

- suíte focada verde;
- `compileall` e `git diff --check` verdes;
- upgrade de cada revisão;
- consulta de `information_schema.columns` confirmando `is_nullable = NO`;
- downgrade de cada bloco e confirmação de `YES` apenas no contrato revertido;
- reaplicação até `head`;
- novo `alembic check` sem divergências de nulabilidade nessas seis tabelas;
- runtime saudável após a reaplicação final.

## Fora de escopo

Este bloco não altera:

- `assets.created_at`, que ainda possui divergência de timezone/tipo;
- `goals`, cujo contrato possui diferenças estruturais maiores;
- `transactions`, cujos timestamps estão ausentes do modelo e fazem parte de um contrato financeiro de alto risco;
- `asset_dividends.dividend_type`.
