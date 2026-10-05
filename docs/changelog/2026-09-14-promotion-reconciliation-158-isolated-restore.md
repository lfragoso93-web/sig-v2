# #158 - restore isolado reconciliado

## Contexto

O artefato `pre-prod-backup.v3` `20260915-002119` havia sido regenerado com
runtime `APP_COMMIT_SHA` igual ao SHA certificado
`48b5041ceaf3240384065c42578fde6689ce17db`. O proximo passo seguro da #158 era
restaurar esse pacote em banco PostgreSQL isolado e descartavel.

## Execucao

Banco isolado criado:

```text
sig-v2-db-1:5432/sgi_restore_20260915_002119
```

Preflight:

- banco criado especificamente para este restore;
- `information_schema.tables WHERE table_schema='public'` retornou 0 antes do
  restore;
- restore executado com `pg_restore --exit-on-error --single-transaction`;
- fonte e alvo tinham identidades de banco diferentes.

## Evidencia

Arquivos gerados no artefato:

- `restore-target-preflight.txt`;
- `restored-inventory.json`;
- `origin-migrations.txt`;
- `restored-migrations.txt`;
- `restore-report.json`;
- `reconciliation-report.json`.

`restore-report.json`:

- `schema_version=pre-prod-restore.v1`;
- `ok=true`;
- dump `database.dump`;
- SHA-256
  `d42efc2f507854b58ab30429530aee10462c3b41ad29467db57ab91dfe77b4c9`;
- target redigido: `sig-v2-db-1:5432/sgi_restore_20260915_002119`.

`reconciliation-report.json`:

- `schema_version=pre-prod-reconciliation.v1`;
- `ok=true`;
- `source_inventory_schema=pre-prod-inventory.v2`;
- `restored_inventory_schema=pre-prod-inventory.v2`;
- migrations de origem:
  `20260906_rate_source32`, `20260910_goals_runtime`;
- migrations restauradas:
  `20260906_rate_source32`, `20260910_goals_runtime`;
- tabelas ausentes: 0;
- tabelas inesperadas: 0;
- divergencias de classificacao: 0;
- divergencias de contagem: 0;
- divergencias de findings: 0.

Seguranca:

- `source_database_writes_executed=0`;
- `restore_target_only=true`;
- `cleanup_executed=false`;
- `rebuild_executed=false`.

## Decisao

O restore isolado do artefato `20260915-002119` esta aprovado para a #158. A
proxima etapa permitida e executar validacoes read-only de reconciliation sobre
o dataset restaurado.

Continuam bloqueados:

- import/rebuild;
- cleanup real;
- migration destrutiva sobre dataset com dados;
- seed global por conveniencia;
- promocao de `ready_for_real_data=true`.
