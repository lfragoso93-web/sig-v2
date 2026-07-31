# Operação — SGI v2

> Última atualização: 22/07/2026

Este guia descreve os comandos de manutenção, validação e diagnóstico do SGI v2.

## Subir o ambiente

```bash
cp .env.example .env
docker compose up -d --build
```

Logs do backend:

```bash
docker compose logs -f backend
```

## Regras operacionais

- trabalhar somente na `stable-15jun`;
- registrar o SHA completo da execução;
- não reutilizar `run_id`, banco isolado ou diretório de artefatos após falha;
- congelar importações e escritas concorrentes quando o runbook exigir;
- não executar limpeza sem inventário, backup, restore, impacto e exportação aprovados;
- tratar o JSON final e o exit code como fontes de verdade.

## Sequência pré-produção

```text
inventário
→ backup
→ restore isolado
→ cleanup impact
→ exportação
→ limpeza controlada (pendente)
→ seeds
→ reimportação
→ posições e snapshots
→ reconciliação final
```

O `full_market_rebuild` não substitui essa sequência: ele reconstrói dados de mercado e snapshots, mas não preserva nem restaura sozinho os dados de negócio exportáveis.

## Inventário read-only

```powershell
docker compose exec backend python -m app.cli.pre_prod_inventory
```

Contrato: `pre-prod-inventory.v2`.

Aprovar somente quando:

- `unclassified_tables=0`;
- `blocking_findings=0`;
- `read_only=true`;
- `writes_executed=0`;
- todas as tabelas possuem classificação e justificativa.

## Backup e restore isolado

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse stable-15jun).Trim()

docker compose exec `
    -e "PRE_PROD_BRANCH=stable-15jun" `
    -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
    backend python -m app.cli.pre_prod_backup --run-id $RunId
```

Contrato: `pre-prod-backup.v3`.

Garantias:

- cliente e servidor PostgreSQL com o mesmo major;
- inventário e dump no mesmo snapshot `REPEATABLE READ READ ONLY`;
- dump custom não vazio;
- inspeção por `pg_restore --list`;
- SHA-256 registrado;
- zero escritas na origem.

Restore em banco vazio e exclusivo:

```powershell
$DbUser = (docker compose exec -T db printenv POSTGRES_USER).Trim()
$DbPassword = (docker compose exec -T db printenv POSTGRES_PASSWORD).Trim()
$RestoreDb = "sgi_restore_$($RunId -replace '-', '_')"

docker compose exec db createdb --username $DbUser $RestoreDb

$EscapedUser = [uri]::EscapeDataString($DbUser)
$EscapedPassword = [uri]::EscapeDataString($DbPassword)
$RestoreUrl = "postgresql://$EscapedUser`:$EscapedPassword@db:5432/$RestoreDb"
$ArtifactDir = "/app/artifacts/pre-prod-rebuild/$RunId"

docker compose exec `
    -e "PRE_PROD_RESTORE_DATABASE_URL=$RestoreUrl" `
    backend python -m app.cli.pre_prod_restore `
    $ArtifactDir --confirm-isolated-target
```

Aprovar somente quando `reconciliation-report.json` apresentar `ok=true`, migrations e tabelas idênticas, zero divergências e zero escritas na origem.

## Dry-run de impacto da limpeza

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse stable-15jun).Trim()

docker compose exec `
    -e "PRE_PROD_BRANCH=stable-15jun" `
    -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
    backend python -m app.cli.pre_prod_cleanup_impact --run-id $RunId
```

Contrato: `pre-prod-cleanup-impact.v2`.

O comando:

- introspecta foreign keys;
- monta o DAG de dependências;
- identifica ciclos e bloqueios;
- confirma o gate de exportação;
- não executa limpeza, exportação ou rebuild.

Runbook: `docs/pre-prod-cleanup-impact-runbook.md`.

## Exportação auditável

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse stable-15jun).Trim()

docker compose exec `
    -e "PRE_PROD_BRANCH=stable-15jun" `
    -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
    backend python -m app.cli.pre_prod_export --run-id $RunId
```

Contrato: `pre-prod-export.v1`.

A exportação aprovada deve conter:

- `transactions`;
- `fixed_income_investments`;
- `corporate_events`;
- CSV determinístico;
- manifesto;
- contagens e bytes;
- SHA-256 de dados e schema;
- `reconciled=true`;
- `source_writes_executed=0`;
- `cleanup_executed=false`;
- `rebuild_executed=false`;
- `overwrite_performed=false`.

A execução real `20260722-134741` exportou 3 tabelas, 323 linhas e 47.576 bytes com exit code `0`.

Runbook: `docs/pre-prod-export-runbook.md`.

## Limpeza controlada

A limpeza executável ainda não está implementada. Até a conclusão do próximo sub-bloco da Issue #158:

- não executar `DELETE`, `TRUNCATE`, `DROP` ou limpeza manual;
- não editar os artefatos aprovados;
- não assumir que `full_market_rebuild` restaura dados de negócio;
- exigir contrato versionado, validação dos artefatos, gate, ordem do DAG, contagens antes/depois e falha atômica.

## Rebuild completo de mercado

```powershell
$LogFile = ".\full-market-rebuild-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

docker compose exec backend python -m app.cli.full_market_rebuild 2>&1 |
    Tee-Object -FilePath $LogFile
```

Etapas:

1. reconciliar catálogo;
2. auditar cobertura histórica;
3. sincronizar lacunas;
4. atualizar Tesouro;
5. atualizar benchmarks;
6. sincronizar o catálogo global de proventos;
7. reconstruir snapshots;
8. gerar auditoria final.

O resultado deve terminar com `ok=false` quando qualquer etapa relevante registrar erro, mesmo que as demais concluam.

## Validação após mudanças estruturais

```powershell
docker compose up -d --build backend
docker compose exec backend python -m app.cli.full_market_rebuild
docker compose logs -f --since 10m backend
```

Validar no frontend:

- Resumo;
- Patrimônio;
- Rentabilidade;
- Proventos;
- importação CSV.

## Sinais de atenção

| Sinal | Interpretação |
|---|---|
| `NumericValueOutOfRangeError` | preço anômalo passou pela validação |
| `number of query arguments cannot exceed 32767` | lote de persistência excessivo |
| `QueuePool limit reached` | sessões longas ou concorrência excessiva |
| muitos `startDate=1900-01-01` | estado de cobertura não persistido corretamente |
| muitos fallbacks lentos | provedor incompatível ainda sendo consultado |
| `has_partial_prices=true` persistente | histórico insuficiente ou classe sem roteamento correto |

## PowerShell e UTF-8

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
```

Terminais antigos podem exibir `NativeCommandError` quando há escrita em `stderr`. Confirme sempre o JSON final e o código de saída.
