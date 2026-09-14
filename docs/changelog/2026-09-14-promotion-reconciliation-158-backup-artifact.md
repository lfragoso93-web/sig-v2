# #158 - artefato candidato aceito

## Contexto

O bloco anterior da #158 estava bloqueado pela ausencia de um artefato local
`pre-prod-backup.v3` aprovado. O backup administrativo `.sql.gz` da interface
nao substitui o contrato de certificacao, porque nao traz o relatorio v3,
inventario de origem, checksum do dump custom e listagem `pg_restore`.

## Evidencia

- caminho host:
  `C:\Users\Acer\Documents\Codex\sgi-v2-backups\20260914-233314`;
- `schema_version=pre-prod-backup.v3`;
- `run_id=20260914-233314`;
- branch `stable-15jun`;
- commit `1e7c3fca6e6acaea19a75c1197f036a1f1021199`;
- `consistent_snapshot=true`;
- `pg_dump_major=16`;
- `server_major=16`;
- `database.dump`: 40.977.216 bytes;
- SHA-256:
  `486d971f25e7924249fac2c8b2630e59b746e16aeaa93bc5dc963093d9e33b81`;
- `source_database_writes_executed=0`;
- `cleanup_executed=false`;
- `rebuild_executed=false`;
- `credentials_recorded=false`.

Inventario de origem:

- `schema_version=pre-prod-inventory.v2`;
- 20 tabelas;
- 4.434.193 linhas;
- 7 tabelas preservadas;
- 2 tabelas `export_before_cleanup`;
- 11 tabelas reconstruiveis;
- 0 tabelas sem classificacao;
- 0 findings bloqueantes.

Validacao local:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\oci_backup_artifact_check.ps1 `
  -BackupDirectory "C:\Users\Acer\Documents\Codex\sgi-v2-backups\20260914-233314"
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
