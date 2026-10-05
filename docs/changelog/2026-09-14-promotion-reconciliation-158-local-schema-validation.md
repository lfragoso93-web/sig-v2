# 2026-09-14 - Validacao local de schema para #158

## Contexto

A primeira validacao read-only da #158 encontrou o banco Docker local sem
tabelas publicas. Para evitar falso positivo sobre banco vazio, o schema local
foi preparado antes de repetir o inventario.

## Execucao

- alvo Git: `9f8a6cc098d64b6b911a690364e7d16219065f3a`;
- banco inicial: `public_tables=0`;
- comando aplicado: cadeia runtime-safe equivalente ao entrypoint, ate
  `20260910_goals_runtime`;
- `alembic current`: `20260910_goals_runtime`;
- tabelas publicas depois da migration: 20.

## Observacao de seguranca

A cadeia Alembic ate `20260910_goals_runtime` inclui a migration
`20260731_drop_legacy_divs`. Neste ambiente local o banco estava vazio antes da
execucao, entao nao havia dataset ou tabelas legadas com dados a preservar.

Essa observacao nao autoriza executar a mesma cadeia sobre um dataset candidato
com dados sem backup, inventario e gate explicito da #158.

## Evidencia read-only

`pre-prod-inventory.v2`:

- `tables=20`;
- `rows=7`;
- `unclassified_tables=0`;
- `blocking_findings=0`;
- `read_only=true`;
- `writes_executed=0`;
- `cleanup_executed=false`;
- `rebuild_executed=false`.

`user-test-readiness.v1`:

- `status=NO_GO`;
- `ready_for_real_data=false`;
- blockers: `assisted_test_data_present`, `market_history_present`;
- warnings: `snapshot_history_present`, `dividends_seed_present`,
  `corporate_events_seed_present`;
- `writes_executed=0`;
- `promotes_ready_for_real_data=false`.

## Decisao

O ambiente local agora possui schema, mas ainda nao possui dataset candidato da
#158. A reconciliation operacional permanece bloqueada ate preparar/restaurar
um dataset aprovado.
