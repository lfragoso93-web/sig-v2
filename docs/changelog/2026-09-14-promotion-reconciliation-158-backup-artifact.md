# #158 - artefato candidato bloqueado por identidade runtime

## Contexto

O bloco anterior da #158 estava bloqueado pela ausencia de um artefato local
`pre-prod-backup.v3`. Um artefato foi gerado e passou nas validacoes
estruturais, mas a checagem posterior encontrou identidade runtime invalida:
o container de origem expunha `APP_COMMIT_SHA=unknown` e o checkout local
inspecionado nao estava no SHA informado ao backup.

O backup administrativo `.sql.gz` da interface nao substitui o contrato de
certificacao, porque nao traz o relatorio v3, inventario de origem, checksum do
dump custom e listagem `pg_restore`.

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

O artefato permanece como evidencia diagnostica, mas nao remove o blocker de
entrada da #158. Ele nao deve ser usado como dataset candidato para restore ate
ser regenerado em runtime cujo `APP_COMMIT_SHA` corresponda exatamente ao SHA
informado na CLI.

A CLI `pre_prod_backup` passa a validar essa identidade antes de abrir a sessao
de backup.

Continuam bloqueados:

- restore candidato;
- import/rebuild;
- cleanup real;
- migration destrutiva sobre dataset com dados;
- seed global por conveniencia;
- promocao de `ready_for_real_data=true`.
