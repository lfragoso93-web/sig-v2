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

Não é feito backfill silencioso. Cada migration conta previamente as linhas incompatíveis e aborta com erro explícito se encontrar qualquer `NULL`.

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

3. `20260807_pos_snap_ts_nn`
   - `portfolio_positions.created_at`;
   - `portfolio_positions.updated_at`;
   - `portfolio_snapshots.created_at`;
   - `portfolio_snapshots.updated_at`.

Cada downgrade restaura `nullable=True`, sem remover defaults nem dados.

## Correção de integridade da revisão

A primeira publicação do terceiro bloco usou o revision ID `20260807_positions_snapshots_ts_nn`, com 34 caracteres. O gate global `test_alembic_revision_integrity.py` detectou corretamente que esse valor excedia o `VARCHAR(32)` de `alembic_version`; a execução local de `upgrade head` também abortou ao tentar persistir o revision ID.

A revisão foi corrigida para `20260807_pos_snap_ts_nn` (22 caracteres), mantendo o mesmo arquivo, `down_revision`, DDL e política defensiva. O gate específico de timestamps agora também exige `len(revision) <= 32`.

## Gates

`test_timestamp_not_null_contraction_migrations.py` protege:

- ordem linear da cadeia;
- presença das tabelas esperadas em cada bloco;
- revision IDs com no máximo 32 caracteres;
- verificação prévia de `NULL`;
- ausência de `UPDATE`, `DELETE`, `TRUNCATE` ou `DROP TABLE`;
- `nullable=False` no upgrade;
- `nullable=True` no downgrade.

## Certificação concluída

A certificação local foi concluída em 07/08/2026:

- suíte focada: `24 passed`;
- `compileall`, `git diff --check` e working tree: verdes;
- banco partiu de `20260807_drop_dup_rate_idx` após o rollback transacional da tentativa com revision ID inválido;
- `upgrade head` aplicou as três migrations e alcançou `20260807_pos_snap_ts_nn (head)`;
- `information_schema.columns` confirmou `is_nullable = NO` nos 12 campos;
- downgrade isolado de `20260807_pos_snap_ts_nn` para `20260807_config_fixed_ts_nn` foi concluído;
- reaplicação do head foi concluída;
- o novo `alembic check` deixou de reportar divergências de nulabilidade nas seis tabelas.

## Fora de escopo após a certificação

Permanecem fora deste bloco e passam a ser tratados separadamente:

- `assets.created_at`, diferença de timezone já classificada como MetaData-only;
- `asset_dividends.dividend_type`, cujo armazenamento físico canônico é `VARCHAR(20)`;
- `goals`, cujo contrato possui diferenças estruturais maiores;
- `transactions`, cujos tipos financeiros e timestamps exigem revisão de consumidores antes de qualquer alinhamento.
