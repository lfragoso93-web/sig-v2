# #158 - backup candidato regenerado com SHA runtime

## Contexto

O artefato `20260914-233314` foi bloqueado porque o container de origem
retornava `APP_COMMIT_SHA=unknown`. Para preservar o contrato de SHA congelado,
foi construida uma imagem backend temporaria a partir do checkout limpo da
`stable-15jun` no SHA `48b5041ceaf3240384065c42578fde6689ce17db`.

O backup foi executado com `APP_COMMIT_SHA` e `--commit-sha` iguais, usando a
rede Docker local do ambiente `sig-v2` para ler o Postgres de origem. O checkout
operacional `E:\Sistema Investimentos\App\SGFP\sig-v2` nao foi alterado.

## Evidencia

- imagem temporaria: `sig-v2-backup:48b5041c`;
- caminho host: `artifacts\pre-prod-rebuild\20260915-002119`;
- `schema_version=pre-prod-backup.v3`;
- `run_id=20260915-002119`;
- branch `stable-15jun`;
- commit `48b5041ceaf3240384065c42578fde6689ce17db`;
- `consistent_snapshot=true`;
- `pg_dump_major=16`;
- `server_major=16`;
- `database.dump`: 40.981.404 bytes;
- SHA-256:
  `d42efc2f507854b58ab30429530aee10462c3b41ad29467db57ab91dfe77b4c9`;
- `source_database_writes_executed=0`;
- `cleanup_executed=false`;
- `rebuild_executed=false`;
- `credentials_recorded=false`.

Inventario de origem:

- `schema_version=pre-prod-inventory.v2`;
- 20 tabelas;
- 4.434.818 linhas;
- 7 tabelas preservadas;
- 2 tabelas `export_before_cleanup`;
- 11 tabelas reconstruiveis;
- 0 tabelas sem classificacao;
- 0 findings bloqueantes.

Validacao local:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\oci_backup_artifact_check.ps1 `
  -BackupDirectory "artifacts\pre-prod-rebuild\20260915-002119"
```

Resultado:

- arquivos obrigatorios presentes;
- `database.dump` nao vazio;
- SHA-256 do dump conferido;
- JSONs parseados com sucesso;
- `database.contents.txt` nao vazio.

## Decisao

O artefato remove o blocker de entrada da #158 e passa a ser o dataset candidato
para o proximo microbloco. A unica acao operacional autorizada a partir dele e
o restore em banco PostgreSQL isolado/descartavel para reconciliacao.

Continuam bloqueados:

- import/rebuild;
- cleanup real;
- migration destrutiva sobre dataset com dados;
- seed global por conveniencia;
- promocao de `ready_for_real_data=true`.
