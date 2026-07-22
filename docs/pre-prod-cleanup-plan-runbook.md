# Runbook — planejamento seguro da limpeza pré-produção

> Estado: implementado em modo `plan-only`; nenhuma escrita no PostgreSQL é autorizada.

## Objetivo

Validar offline os artefatos aprovados da execução e publicar o contrato
`pre-prod-cleanup-execution.v1` sem acessar o banco e sem executar limpeza ou
rebuild.

## Pré-requisitos

- trabalhar na branch `stable-15jun`;
- usar o SHA completo da branch;
- usar um `run_id` não reutilizado;
- possuir `cleanup-impact.json` aprovado;
- possuir `export/manifest.json` e todos os CSVs exportados;
- não editar os artefatos após a exportação.

## Comando

```powershell
$RunId = "<run-id-da-exportacao>"
$CommitSha = (git rev-parse stable-15jun).Trim()

# O commit da CLI deve estar presente na imagem antes da execução.
docker compose up -d --build backend

docker compose exec `
    -e "PRE_PROD_BRANCH=stable-15jun" `
    -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
    backend python -m app.cli.pre_prod_cleanup_plan `
    --run-id $RunId
```

Caminhos padrão:

```text
artifacts/pre-prod-rebuild/<run-id>/cleanup-impact.json
artifacts/pre-prod-rebuild/<run-id>/export/manifest.json
artifacts/pre-prod-rebuild/<run-id>/export/tables/*.csv
```

Artefato publicado:

```text
artifacts/pre-prod-rebuild/<run-id>/cleanup/plan.json
```

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

## Códigos de saída

| Código | Significado |
|---:|---|
| `0` | plano validado e publicado |
| `1` | falha inesperada |
| `2` | identidade operacional ausente |
| `3` | gate, checksum ou artefato inválido |
| `4` | plano já existente; sobrescrita recusada |
| `130` | execução interrompida |

## Critérios de aprovação

O JSON final deve registrar:

- `schema_version=pre-prod-cleanup-execution.v1`;
- `database_accessed=false`;
- `database_writes_executed=0`;
- `cleanup_executed=false`;
- `safety.plan_only=true`;
- correspondência exata entre o DAG e os artefatos exportados.

Este comando não autoriza a limpeza real. `DELETE`, `TRUNCATE`, `DROP`, rebuild e
restauração dos dados exportados permanecem fora de escopo até um bloco posterior
explicitamente aprovado na Issue #158.
