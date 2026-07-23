# Runbook — ensaio da limpeza controlada em banco isolado

## Estado

Este documento prepara o Bloco D da Issue #196. Ele não autoriza limpeza na base pré-produção real e não deve ser usado fora de um banco PostgreSQL descartável restaurado de um backup `pre-prod-backup.v3` reconciliado.

A implementação da CLI, do executor transacional e dos relatórios de `committed`, `aborted` e `rolled_back` foi validada em Windows com 44 testes aprovados e compilação Python sem erros.

## Objetivo do ensaio

Comprovar, em PostgreSQL descartável, que a limpeza:

1. consome exatamente um `cleanup/plan.json` aprovado;
2. recusa origem, destino não isolado, SHA ou checksum divergente;
3. valida todas as contagens antes da primeira escrita;
4. executa somente as tabelas da ordem canônica do plano;
5. preserva integralmente as tabelas fora do conjunto de limpeza;
6. publica `cleanup/execution.json` sem credenciais;
7. produz rollback integral em cenário de falha controlada;
8. não inicia coleta, seed, importação ou rebuild;
9. termina com descarte explícito do banco do ensaio.

## Escopo autorizado

- banco PostgreSQL descartável, criado exclusivamente para o ensaio;
- restauração de backup v3 já validado;
- consultas de inventário e reconciliação;
- execução da CLI de limpeza contra o banco descartável;
- criação e remoção do banco descartável pelo operador.

## Operações proibidas

- apontar `--target-database-url` para a origem;
- executar contra a base pré-produção real;
- reutilizar banco que contenha dados não descartáveis;
- executar `DROP TABLE`, `TRUNCATE`, DDL ou `CASCADE` para contornar falhas;
- editar manualmente `cleanup/plan.json` ou seus checksums;
- iniciar seed, coleta, COTAHIST, Tesouro, benchmarks, proventos, CSV ou snapshots;
- promover automaticamente a autorização do ensaio para outro ambiente.

## Identidade obrigatória do ensaio

Use um nome novo e inequívoco, por exemplo:

```text
sgi_cleanup_rehearsal_20260723
```

O nome deve:

- ser diferente do banco de origem;
- conter indicação explícita de ensaio ou isolamento;
- existir apenas durante o Bloco D;
- estar vazio antes da restauração;
- ser descartado após a coleta das evidências.

Marcador obrigatório da CLI:

```text
sgi-pre-prod-isolated
```

## Pré-requisitos

Antes de qualquer restauração ou limpeza, confirmar:

- [ ] branch local exatamente `stable-15jun`;
- [ ] working tree limpa;
- [ ] commit SHA completo registrado;
- [ ] containers backend, PostgreSQL e Redis saudáveis;
- [ ] diretório do backup v3 existente;
- [ ] `backup-manifest.json` com schema v3 e `consistent_snapshot=true`;
- [ ] checksum do archive validado;
- [ ] `reconciliation-report.json` do restore anterior, quando houver, não reutilizado como evidência nova;
- [ ] novo banco de ensaio inexistente ou vazio;
- [ ] URL de origem e URL de destino diferentes;
- [ ] nenhum processo de coleta, seed ou rebuild em execução;
- [ ] novo `run_id` reservado para o ensaio;
- [ ] `cleanup/plan.json` aprovado e não alterado.

Qualquer item não confirmado interrompe o bloco.

## Variáveis PowerShell

Os valores abaixo são exemplos. Não grave senhas no repositório, histórico de shell ou artefatos.

```powershell
$BackupRunId = "<run-id-do-backup-v3>"
$CleanupRunId = "<novo-run-id-do-ensaio>"
$CommitSha = (git rev-parse HEAD).Trim()
$ArtifactRoot = "artifacts/pre-prod-rebuild"
$BackupDirectory = "$ArtifactRoot/$BackupRunId"
$PlanPath = "$ArtifactRoot/$CleanupRunId/cleanup/plan.json"
$TargetDatabase = "sgi_cleanup_rehearsal_20260723"
$TargetDatabaseUrl = "postgresql://<usuario>:<senha>@db:5432/$TargetDatabase"
$SourceDatabaseUrl = "<url-sincrona-da-origem>"
$IsolationMarker = "sgi-pre-prod-isolated"
```

A URL usada pela CLI de limpeza deve ser PostgreSQL síncrona, sem `+asyncpg`.

## Gate 1 — confirmar branch, SHA e estado local

```powershell
git branch --show-current
git status --short
git rev-parse HEAD
```

Resultado obrigatório:

- branch `stable-15jun`;
- nenhuma alteração local não intencional;
- SHA igual ao que será fornecido à restauração, ao plano e à limpeza.

## Gate 2 — validar o backup v3 sem restaurar

```powershell
Get-Content "$BackupDirectory/backup-manifest.json" -Raw | ConvertFrom-Json | Format-List
Get-FileHash "$BackupDirectory/database.dump" -Algorithm SHA256
```

Confirmar manualmente:

- schema `pre-prod-backup.v3`;
- snapshot consistente;
- archive não vazio;
- SHA-256 igual ao manifesto;
- branch e commit esperados.

## Gate 3 — criar banco descartável vazio

A criação do banco é uma ação administrativa fora da CLI de limpeza. Execute somente após conferir que o nome é novo e descartável.

Exemplo dentro do container PostgreSQL:

```powershell
docker compose exec db psql -U postgres -d postgres -v ON_ERROR_STOP=1 `
    -c "CREATE DATABASE $TargetDatabase;"
```

Antes de prosseguir, confirme que o destino não é a origem e que não contém tabelas de aplicação.

```powershell
docker compose exec db psql -U postgres -d $TargetDatabase -v ON_ERROR_STOP=1 `
    -c "SELECT current_database(), count(*) AS application_tables FROM information_schema.tables WHERE table_schema = 'public';"
```

Se o banco já existir, contiver tabelas ou não puder ser identificado inequivocamente como descartável, interrompa o ensaio.

## Gate 4 — restaurar o backup v3

```powershell
docker compose exec `
    -e "PRE_PROD_RESTORE_DATABASE_URL=$TargetDatabaseUrl" `
    backend python -m app.cli.pre_prod_restore `
    "$BackupDirectory" `
    --confirm-isolated-target

$RestoreExitCode = $LASTEXITCODE
if ($RestoreExitCode -ne 0) {
    throw "Restauração isolada falhou com exit code $RestoreExitCode"
}
```

Artefatos obrigatórios após a restauração:

```text
restored-inventory.json
origin-migrations.txt
restored-migrations.txt
reconciliation-report.json
```

O `reconciliation-report.json` deve indicar `ok=true`. Qualquer divergência interrompe o ensaio antes da limpeza.

## Gate 5 — validar o plano aprovado

```powershell
$Plan = Get-Content $PlanPath -Raw | ConvertFrom-Json
$Plan | Format-List
$PlanChecksum = (Get-FileHash $PlanPath -Algorithm SHA256).Hash.ToLowerInvariant()
```

Atenção: a confirmação da CLI usa o checksum canônico calculado pelo gerador do plano, não um checksum textual improvisado. Utilize o valor registrado pelo artefato aprovado ou pela saída canônica correspondente.

Confirmar:

- schema `pre-prod-cleanup-execution.v1`;
- modo `plan`;
- branch `stable-15jun`;
- commit igual a `$CommitSha`;
- blockers vazios;
- ordem de limpeza presente;
- `database_writes_executed=0` no histórico do plano;
- `cleanup_executed=false`;
- `rebuild_executed=false`.

## Gate 6 — registrar baseline das tabelas preservadas

Antes da limpeza, capture contagens das tabelas classificadas como preservadas usando o inventário restaurado e salve a evidência fora do banco.

Não crie uma segunda classificação manual. A lista deve vir do contrato canônico de inventário usado pelo backup e pelo plano.

Artefato esperado do operador:

```text
artifacts/pre-prod-rebuild/<cleanup-run-id>/cleanup/preserved-before.json
```

Esse arquivo não é produzido automaticamente pela CLI neste estágio e deve ser obtido por procedimento read-only auditável antes do ensaio real.

## Gate 7 — construir confirmação composta

```powershell
$PlanCanonicalSha256 = "<plan-sha256-canônico>"
$Confirmation = "CLEANUP $CleanupRunId ON $TargetDatabase AT $CommitSha WITH $PlanCanonicalSha256"
```

Revise visualmente todos os componentes. Não reutilize confirmação de outra execução.

## Execução controlada

Somente após todos os gates anteriores:

```powershell
docker compose exec backend python -m app.cli.pre_prod_isolated_cleanup `
    --plan "$PlanPath" `
    --artifact-root "$ArtifactRoot" `
    --branch "stable-15jun" `
    --commit-sha "$CommitSha" `
    --source-database-url "$SourceDatabaseUrl" `
    --target-database-url "$TargetDatabaseUrl" `
    --target-isolation-marker "$IsolationMarker" `
    --confirmation "$Confirmation"

$CleanupExitCode = $LASTEXITCODE
```

Não execute novamente com o mesmo `run_id`, mesmo após falha.

## Interpretação do resultado

- `0`: commit concluído e `execution.json` publicado;
- `20`: divergência de contagem antes da primeira escrita;
- `21`: lock operacional indisponível;
- `22`: transação revertida;
- `30`: falha ao publicar evidência;
- qualquer outro código: ensaio não aprovado.

Artefato obrigatório:

```text
artifacts/pre-prod-rebuild/<cleanup-run-id>/cleanup/execution.json
```

O relatório deve conter apenas o alvo redigido `host:port/database`, nunca usuário, senha ou URL completa.

## Reconciliação pós-execução

Para aprovar o cenário de sucesso, confirmar:

- [ ] `final_state=committed`;
- [ ] `committed=true`;
- [ ] `lock_acquired=true`;
- [ ] todas as tabelas planejadas com `actual_rows_after=0`;
- [ ] totais reconciliados;
- [ ] `preserved_tables_unchanged=true`;
- [ ] `rebuild_started=false`;
- [ ] nenhuma tabela fora do plano recebeu escrita;
- [ ] inventário pós-limpeza sem schema alterado;
- [ ] baseline e pós-execução das tabelas preservadas idênticos.

Evidências adicionais esperadas:

```text
cleanup/preserved-after.json
cleanup/post-cleanup-inventory.json
cleanup/reconciliation.json
```

A geração automática desses três artefatos ainda deve ser implementada ou formalizada antes da execução real do Bloco D.

## Cenário obrigatório de rollback

O Bloco D não estará concluído apenas com o cenário de sucesso. Deve existir um segundo banco descartável ou nova restauração limpa com novo `run_id` para comprovar rollback.

A falha deve ser induzida por mecanismo controlado de teste ou divergência segura, nunca por edição do plano aprovado, DDL, `CASCADE` ou intervenção parcial na transação.

Resultado obrigatório:

- exit code `22` ou código de aborto esperado;
- `final_state=rolled_back` ou `aborted`;
- `committed=false`;
- zero escritas persistidas;
- contagens finais iguais ao baseline restaurado;
- tabelas preservadas inalteradas;
- artefato sem credenciais.

## Descarte do banco

Depois que todas as evidências forem copiadas e validadas:

```powershell
docker compose exec db psql -U postgres -d postgres -v ON_ERROR_STOP=1 `
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$TargetDatabase' AND pid <> pg_backend_pid();"

docker compose exec db psql -U postgres -d postgres -v ON_ERROR_STOP=1 `
    -c "DROP DATABASE $TargetDatabase;"
```

Confirme o descarte:

```powershell
docker compose exec db psql -U postgres -d postgres -tAc `
    "SELECT 1 FROM pg_database WHERE datname = '$TargetDatabase';"
```

A saída deve estar vazia.

## Critério de aprovação do Bloco D

O ensaio somente será aprovado quando existirem:

1. restauração v3 reconciliada;
2. execução bem-sucedida reconciliada;
3. cenário de rollback ou aborto reconciliado;
4. tabelas preservadas comprovadamente inalteradas;
5. ausência de rebuild, seed e coleta;
6. artefatos sem credenciais;
7. banco descartável removido;
8. evidências registradas na Issue #196 e na PR #198.

Até lá, a limpeza na base pré-produção real permanece proibida.
