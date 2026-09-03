# Runbook — Exportação auditável pré-produção

## Objetivo

Executar a exportação read-only dos dados classificados como não reconstruíveis pelo contrato `pre-prod-cleanup-impact.v2`, preservando contagens, schema, checksums e rastreabilidade para auditoria e evidência de preservação.

Este procedimento não executa limpeza, seed, importação, rebuild ou qualquer comando de escrita na origem.

## Escopo

A CLI exporta exclusivamente as tabelas classificadas pelo gate como `export_required`:

- `transactions`;
- `corporate_events`.

A lista efetiva é derivada do cleanup impact no mesmo snapshot da exportação. A operação aborta se o gate não estiver aprovado ou se as contagens exportadas divergirem da origem.

No contrato corrente pós-`20260903_drop_fixed_income`, a lista efetiva contém `transactions` e `corporate_events`. Runs históricos executados por SHAs anteriores podem conter `fixed_income_investments.csv`; esse artefato continua válido como evidência histórica, mas não é exigido por uma nova execução.

Este export seletivo não possui contrato de reidratação. Para recuperação operacional use o dump completo `pre-prod-backup.v3` e o fluxo aprovado de restore em banco vazio.

## Contratos e garantias

- cleanup impact: `pre-prod-cleanup-impact.v2`;
- manifesto: `pre-prod-export.v1`;
- branch obrigatória: `stable-15jun`;
- commit obrigatório: SHA Git completo com 40 caracteres;
- transação: PostgreSQL `REPEATABLE READ, READ ONLY`;
- uma única sessão para inventário, cleanup impact e exportação;
- CSV UTF-8 com cabeçalho e colunas na ordem do schema;
- SHA-256 separado para dados e schema;
- publicação por rename atômico;
- recusa de sobrescrita para o mesmo run-id;
- rollback obrigatório ao encerrar a sessão;
- remoção do diretório publicado quando a reconciliação de contagens falha.

## Pré-requisitos

1. Estar no repositório `lfragoso93-web/sig-v2`.
2. Estar na branch `stable-15jun` sem alterações locais pendentes.
3. Ter sincronizado a branch com a `main`.
4. Ter o Docker Desktop ativo.
5. Ter o backend configurado para o PostgreSQL real de pré-produção.
6. Confirmar que o backup validado da Issue #183 permanece disponível.
7. Confirmar que não há processo de limpeza, seed, importação ou rebuild em execução.
8. Usar um run-id novo e exclusivo.

## Verificações antes da execução

No PowerShell:

```powershell
git status --short
git branch --show-current
git fetch origin
git rev-list --left-right --count origin/main...HEAD
```

Resultado esperado:

- branch atual: `stable-15jun`;
- working tree limpa;
- zero commits atrás da `main`.

Subir os serviços:

```powershell
docker compose up -d --build

docker compose ps
```

O backend, PostgreSQL e Redis devem estar ativos e saudáveis.

## Execução

Gerar identificadores:

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse HEAD).Trim()
```

Executar a exportação dentro do container backend:

```powershell
docker compose exec `
    -e "PRE_PROD_BRANCH=stable-15jun" `
    -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
    backend python -m app.cli.pre_prod_export --run-id $RunId
```

A CLI também aceita os parâmetros explicitamente:

```powershell
docker compose exec backend python -m app.cli.pre_prod_export `
    --branch stable-15jun `
    --commit-sha $CommitSha `
    --run-id $RunId
```

Não executar novamente com o mesmo run-id.

## Exit codes

| Código | Significado | Ação |
| --- | --- | --- |
| `0` | exportação concluída e contagens reconciliadas | seguir para validação dos artefatos |
| `1` | erro operacional, argumento inválido ou falha inesperada | preservar logs, investigar e não avançar |
| `2` | gate `pre-prod-cleanup-impact.v2` bloqueado | revisar blockers; não exportar nem limpar |
| `3` | contagens exportadas divergentes do snapshot | tratar como bloqueante; diretório publicado é removido |
| `130` | execução interrompida | confirmar ausência de artefatos parciais antes de repetir com novo run-id |

No PowerShell, capturar o código logo após o comando:

```powershell
$ExitCode = $LASTEXITCODE
$ExitCode
```

Somente o código `0` permite continuar.

## Estrutura dos artefatos

Diretório padrão:

```text
artifacts/pre-prod-rebuild/<run-id>/export/
├── manifest.json
└── tables/
    ├── corporate_events.csv
    └── transactions.csv
```

Os artefatos são dados operacionais e não devem ser adicionados ao Git.

## Validação obrigatória

### 1. Confirmar os arquivos

```powershell
$ExportDir = "artifacts/pre-prod-rebuild/$RunId/export"
Get-ChildItem -Recurse $ExportDir
```

Devem existir `manifest.json` e um CSV para cada tabela listada em `source.exported_tables`.

### 2. Validar JSON e resultado reconciliado

A saída da CLI deve conter:

```json
{
  "reconciled": true
}
```

O manifesto deve conter:

- `schema_version` igual a `pre-prod-export.v1`;
- `branch` igual a `stable-15jun`;
- `commit_sha` igual ao SHA executado;
- `run_id` igual ao identificador da execução;
- `source.transaction_isolation` igual a `repeatable read`;
- `source.read_only` igual a `true`;
- exatamente as tabelas aprovadas pelo gate;
- contagens de linhas e bytes;
- checksums SHA-256 de dados e schema;
- indicadores de segurança sem escrita, cleanup, rebuild ou overwrite.

### 3. Recalcular checksums dos CSVs

```powershell
Get-ChildItem "$ExportDir/tables/*.csv" | ForEach-Object {
    [PSCustomObject]@{
        File = $_.Name
        SHA256 = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
        Bytes = $_.Length
    }
}
```

Cada hash deve corresponder ao campo `data_sha256` da tabela no manifesto.

### 4. Validar UTF-8

```powershell
Get-ChildItem "$ExportDir/tables/*.csv" | ForEach-Object {
    $null = Get-Content $_.FullName -Encoding UTF8 -ErrorAction Stop
    Write-Host "UTF-8 OK: $($_.Name)"
}
```

Qualquer erro de leitura bloqueia o avanço.

### 5. Validar contagens de linhas

Cada CSV contém uma linha de cabeçalho. A quantidade de dados é `linhas físicas - 1`.

```powershell
Get-ChildItem "$ExportDir/tables/*.csv" | ForEach-Object {
    $PhysicalLines = (Get-Content $_.FullName -Encoding UTF8).Count
    [PSCustomObject]@{
        File = $_.Name
        DataRows = [Math]::Max(0, $PhysicalLines - 1)
    }
}
```

Esta verificação é auxiliar. Campos com quebra de linha válida podem ocupar mais de uma linha física; a contagem canônica é a registrada pelo escritor CSV e reconciliada no mesmo snapshot. Em caso de diferença, validar com um parser CSV antes de concluir divergência.

### 6. Confirmar zero escrita na origem

O manifesto deve registrar:

- `source_read_only: true`;
- `source_writes_executed: 0`;
- `cleanup_executed: false`;
- `rebuild_executed: false`;
- `overwrite_performed: false`.

Não executar comandos corretivos no banco durante esta etapa.

## Critérios de aprovação

A execução é aprovada somente quando todos os itens abaixo forem verdadeiros:

- exit code `0`;
- `reconciled=true`;
- gate aprovado e sem blockers;
- três tabelas exportadas ou exatamente o conjunto canônico indicado pelo gate;
- contagens do manifesto iguais às contagens do cleanup impact do mesmo snapshot;
- checksums recalculados iguais aos do manifesto;
- arquivos legíveis em UTF-8;
- branch e SHA corretos;
- zero escrita, cleanup, seed, importação ou rebuild;
- artefatos armazenados fora do Git.

## Critérios de aborto

Interromper e não avançar para limpeza quando ocorrer qualquer um dos seguintes:

- exit code diferente de `0`;
- gate bloqueado;
- tabela inesperada ou ausente;
- divergência de contagem;
- checksum divergente;
- manifesto inválido;
- erro de UTF-8;
- branch ou SHA incorretos;
- indício de escrita na origem;
- artefato preexistente para o run-id;
- execução simultânea de manutenção no banco.

## Recuperação após falha

1. Não reutilizar o run-id.
2. Preservar stdout, stderr e o exit code.
3. Verificar se existe `artifacts/pre-prod-rebuild/<run-id>/.export.tmp`.
4. Não apagar artefatos de uma execução aprovada.
5. Corrigir a causa em commit pequeno na `stable-15jun`.
6. Executar CI novamente.
7. Repetir a operação com novo run-id.

A CLI remove o diretório temporário em falhas do serviço e remove o diretório publicado quando a reconciliação falha. Qualquer resíduo deve ser tratado como evidência de uma execução incompleta.

## Evidências para a Issue #188

Registrar na Issue #188:

- data e hora UTC;
- run-id;
- branch;
- commit SHA;
- exit code;
- conjunto de tabelas;
- contagens por tabela;
- total de linhas e bytes;
- SHA-256 por CSV;
- resultado da validação UTF-8;
- `reconciled=true`;
- confirmação de zero escrita;
- caminho seguro onde os artefatos foram armazenados;
- conclusão objetiva: aprovado ou bloqueado.

Não publicar dados pessoais, conteúdo dos CSVs, credenciais ou URLs com segredos.

## Próximos passos após aprovação

1. Sincronizar README, ROADMAP e CHANGELOG com a evidência real.
2. Atualizar a descrição da PR #191.
3. Marcar a PR como pronta para revisão.
4. Promover para `main` somente após todos os checks verdes.
5. Encerrar a Issue #188 após o merge e a confirmação documental.
6. Manter limpeza, restauração e reimportação fora deste bloco.
