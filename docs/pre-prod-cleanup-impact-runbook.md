# Dry-run de impacto da limpeza pré-produção

Este procedimento gera o contrato auditável `pre-prod-cleanup-impact.v2`. A execução consulta inventário, contagens e foreign keys no mesmo snapshot transacional e termina com rollback.

## Pré-requisitos

- branch `stable-15jun`;
- SHA completo do commit;
- backend e PostgreSQL disponíveis;
- diretório de artefatos gravável.

## Execução em PowerShell

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse HEAD).Trim()

docker compose exec `
    -e "PRE_PROD_BRANCH=stable-15jun" `
    -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
    backend python -m app.cli.pre_prod_cleanup_impact --run-id $RunId

$ExitCode = $LASTEXITCODE
Write-Host "Exit code: $ExitCode"
```

Artefato gerado:

```text
artifacts/pre-prod-rebuild/<run-id>/cleanup-impact.json
```

Uma execução existente não é sobrescrita. O mesmo `run-id` não pode ser reutilizado.

## Códigos de saída

- `0`: relatório aprovado, sem bloqueadores;
- `2`: relatório gerado com bloqueadores;
- `1`: falha operacional ou entrada inválida;
- `130`: execução interrompida.

## Critérios de aborto

Não avançar para qualquer etapa posterior quando ocorrer uma destas condições:

- `ok` diferente de `true`;
- `blockers` não vazio;
- tabela `unclassified`;
- ciclo em `dependency_plan.cycles`;
- foreign key fora do inventário;
- tabela preservada na ordem de limpeza;
- tabela exportável fora de `export_required_before_cleanup`;
- ordem de rebuild incompatível com as tabelas reconstruíveis;
- `safety.read_only` diferente de `true`;
- `safety.writes_executed` diferente de `0`;
- `safety.cleanup_executed` ou `safety.rebuild_executed` igual a `true`;
- branch ou SHA divergentes da execução;
- artefato ausente ou JSON inválido;
- código de saída diferente de `0`.

## Revisão do artefato

Confirmar:

1. schema `pre-prod-cleanup-impact.v2`;
2. branch `stable-15jun`;
3. SHA igual ao `git rev-parse HEAD`;
4. todas as tabelas classificadas;
5. tabelas preservadas fora da ordem de limpeza;
6. tabelas exportáveis no gate obrigatório;
7. tabelas reconstruíveis exatamente na ordem de rebuild;
8. dependências e constraints registradas;
9. ausência de ciclos;
10. modo read-only e zero escrita.

Este runbook apenas produz evidência para revisão na Issue #185.
