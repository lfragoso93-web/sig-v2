# Runbook — planejamento seguro da limpeza pré-produção

> Estado: implementado em modo `plan-only`; nenhuma escrita no PostgreSQL é autorizada.

## Objetivo

Validar offline os artefatos aprovados da execução e publicar o contrato
`pre-prod-cleanup-execution.v1` sem acessar o banco e sem executar limpeza ou
rebuild.

Este runbook cobre a validação real da Issue #195, vinculada à Issue #158. A
aprovação deste procedimento não autoriza a limpeza do PostgreSQL.

## Pré-requisitos

- trabalhar na branch `stable-15jun`;
- sincronizar a branch com a `main` antes da execução;
- usar o SHA completo da branch;
- usar um `run_id` novo e não reutilizado;
- subir a imagem backend contendo a PR #194;
- possuir acesso ao PostgreSQL real usado no dry-run e na exportação;
- não editar, mover ou recriar os artefatos após a exportação;
- interromper imediatamente se qualquer comando retornar código diferente de zero.

## Cadeia completa de validação real

Execute a exportação e o plano usando exatamente o mesmo `run_id`, branch e SHA.

```powershell
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding

$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse stable-15jun).Trim()

if ((git branch --show-current).Trim() -ne "stable-15jun") {
    throw "A execução deve ocorrer exclusivamente na stable-15jun."
}

if ($CommitSha.Length -ne 40) {
    throw "O SHA da execução deve possuir 40 caracteres."
}

docker compose up -d --build backend

docker compose exec `
    -e "PRE_PROD_BRANCH=stable-15jun" `
    -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
    backend python -m app.cli.pre_prod_export --run-id $RunId

if ($LASTEXITCODE -ne 0) {
    throw "A exportação falhou com exit code $LASTEXITCODE. Não execute o plano."
}

docker compose exec `
    -e "PRE_PROD_BRANCH=stable-15jun" `
    -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
    backend python -m app.cli.pre_prod_cleanup_plan `
    --run-id $RunId

if ($LASTEXITCODE -ne 0) {
    throw "O planejamento falhou com exit code $LASTEXITCODE."
}

Write-Host "RunId validado: $RunId"
Write-Host "Commit validado: $CommitSha"
```

Não gere um segundo SHA entre os dois comandos. Não reutilize um diretório de
execução anterior, mesmo quando a tentativa anterior tiver falhado.

## Caminhos padrão

```text
artifacts/pre-prod-rebuild/<run-id>/cleanup-impact.json
artifacts/pre-prod-rebuild/<run-id>/export/manifest.json
artifacts/pre-prod-rebuild/<run-id>/export/tables/*.csv
```

Artefato publicado:

```text
artifacts/pre-prod-rebuild/<run-id>/cleanup/plan.json
```

## Inspeção dos artefatos

Copie os JSONs para inspeção no host sem alterá-los no container:

```powershell
$ArtifactRoot = ".\artifacts\pre-prod-rebuild\$RunId"
New-Item -ItemType Directory -Force -Path $ArtifactRoot | Out-Null

docker compose cp "backend:/app/artifacts/pre-prod-rebuild/$RunId/cleanup-impact.json" `
    "$ArtifactRoot\cleanup-impact.json"

docker compose cp "backend:/app/artifacts/pre-prod-rebuild/$RunId/export/manifest.json" `
    "$ArtifactRoot\manifest.json"

docker compose cp "backend:/app/artifacts/pre-prod-rebuild/$RunId/cleanup/plan.json" `
    "$ArtifactRoot\plan.json"
```

A cópia serve somente para auditoria. Os checksums são calculados e validados
contra os artefatos originais da execução no container.

## Validações obrigatórias

A CLI falha fechada quando houver:

- branch diferente de `stable-15jun`;
- SHA ou `run_id` divergente;
- cleanup impact sem aprovação, com blockers ou ciclos;
- ordem do DAG inválida ou duplicada;
- checksum divergente do cleanup impact, manifesto ou CSV;
- tabela exportável ausente ou adicional;
- artefato fora do diretório da execução;
- plano já publicado para o mesmo `run_id`.

## Critérios da exportação

Antes de aceitar o plano, o JSON final de `pre_prod_export` deve registrar:

- `reconciled=true`;
- `source_writes_executed=0`;
- `cleanup_executed=false`;
- `rebuild_executed=false`;
- `overwrite_performed=false`;
- exatamente as tabelas `transactions` e `corporate_events` classificadas como `export_before_cleanup` no inventário corrente;
- exit code `0`.

Artefatos históricos anteriores a `20260903_drop_fixed_income` podem registrar uma terceira tabela, `fixed_income_investments`. Essa evidência deve ser mantida com o run original e não altera o critério das execuções correntes.

## Critérios do plano

O JSON final e `cleanup/plan.json` devem registrar:

- `schema_version=pre-prod-cleanup-execution.v1`;
- mesmo `run_id`, branch e SHA da exportação;
- `plan_sha256` na saída da CLI, calculado sobre o mesmo JSON canônico que a
  CLI de limpeza revalida;
- `database_accessed=false`;
- `database_writes_executed=0`;
- `cleanup_executed=false`;
- `safety.plan_only=true`;
- `safety.rebuild_executed=false`;
- `safety.artifact_overwrite_performed=false`;
- `safety.reusable_run_id=false`;
- `blockers=[]`;
- correspondência exata entre o DAG e os artefatos exportados.

O campo `plan_sha256` pertence ao envelope de saída da CLI e não é gravado
dentro de `cleanup/plan.json`, evitando um checksum autorreferente. Esse valor é
a fonte oficial para construir a confirmação composta. Não o substitua por
`Get-FileHash`, pois o hash de bytes formatados pode diferir do JSON canônico.

## Códigos de saída

| Código | Significado |
|---:|---|
| `0` | plano validado e publicado |
| `1` | falha inesperada |
| `2` | identidade operacional ausente |
| `3` | gate, checksum ou artefato inválido |
| `4` | plano já existente; sobrescrita recusada |
| `130` | execução interrompida |

## Critérios de aborto

Abortar o bloco e não prosseguir para qualquer limpeza quando:

- qualquer comando retornar código diferente de zero;
- o backend não estiver executando o SHA registrado;
- o `run_id` já existir;
- a exportação não estiver reconciliada;
- houver divergência de contagem, tabela, DAG ou checksum;
- qualquer indicador de escrita ou execução de cleanup/rebuild for diferente do
  valor seguro esperado;
- os JSONs finais estiverem incompletos ou não puderem ser preservados.

## Registro obrigatório na Issue #195

Ao concluir a execução, registrar:

- `run_id`;
- SHA completo;
- exit code da exportação;
- exit code do plano;
- tabelas, linhas e bytes exportados;
- `reconciled`;
- checksums do cleanup impact, manifesto e CSVs;
- `plan_sha256` canônico emitido pela CLI;
- invariantes de segurança do `plan.json`;
- confirmação explícita de zero escrita e zero limpeza.

Este comando não autoriza a limpeza real. `DELETE`, `TRUNCATE`, `DROP`, rebuild e
restauração dos dados exportados permanecem fora de escopo até um bloco posterior
explicitamente aprovado e documentado na Issue #158.
