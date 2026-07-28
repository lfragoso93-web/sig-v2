# Runbook — seed isolado de câmbio

## Objetivo

Executar exclusivamente o seed canônico de câmbio `USD-BRL` com PTAX de venda oficial do Banco Central do Brasil, em transação única, com advisory lock dedicado e evidência JSON auditável.

Este estágio não executa B3, Tesouro, benchmarks, proventos, importação CSV, posições ou snapshots.

## Contrato operacional

- Schema: `pre-prod-fx-seed.v1`
- Branch obrigatória: `stable-15jun`
- Par suportado: `USD-BRL`
- Tipo de taxa: `PTAX_SELL`
- Fonte: `BCB`
- Identidade obrigatória:
  - `run_id` no formato `YYYYMMDD-HHMMSS`
  - branch `stable-15jun`
  - SHA completo, hexadecimal minúsculo, com 40 caracteres
- Intervalo obrigatório:
  - `start_date`
  - `end_date`

## Arquitetura

Fluxo transacional:

```text
inspect -> prepare -> flush -> inspect -> commit/rollback
```

Garantias:

- advisory lock exclusivo;
- sessões separadas para lock e trabalho;
- cliente PTAX estrito, sem fallback;
- persistência com `commit=False` durante a preparação;
- commit somente após inspeção final válida;
- rollback em duplicidades, pares não suportados ou exceções;
- liberação do lock em `finally`;
- nenhuma credencial exposta em falhas inesperadas.

A consulta `CotacaoDolarPeriodo` não deve enviar `$orderby`, pois o endpoint oficial rejeita essa opção com HTTP 400. A ordenação cronológica, a deduplicação diária e a escolha do boletim mais recente são realizadas pelo parser local.

## Pré-requisitos

1. Checkout limpo da `stable-15jun`.
2. `HEAD` aprovado e registrado na Issue operacional correspondente.
3. Backend, PostgreSQL e Redis disponíveis.
4. Acesso de saída ao endpoint oficial da PTAX.
5. Diretório de artefatos existente no host.
6. Intervalo curto e previamente aprovado para o primeiro ensaio.
7. Rebuild da imagem backend após qualquer atualização do checkout, pois o código não é montado como volume.

## Validação unitária

No host, em PowerShell:

```powershell
git pull --ff-only origin stable-15jun

pytest -q `
    backend/tests/unit/test_pre_prod_fx_seed_cli.py `
    backend/tests/unit/test_pre_prod_fx_seed_service.py `
    backend/tests/unit/test_pre_prod_fx_seed_preparation.py `
    backend/tests/unit/test_bcb_ptax_strict.py `
    backend/tests/unit/test_pre_prod_fx_seed_contract.py `
    backend/tests/unit/test_pre_prod_fx_seed_inspection.py `
    backend/tests/unit/test_fx_persistence.py `
    backend/tests/unit/test_settings_env.py
```

## Primeira execução controlada

Exemplo para uma janela curta de dias úteis:

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse HEAD).Trim()
$StartDate = "2026-07-20"
$EndDate = "2026-07-24"
$ArtifactDir = "artifacts/pre-prod-fx-seed/$RunId"
$ArtifactPath = "$ArtifactDir/fx-seed.json"

New-Item -ItemType Directory -Force -Path $ArtifactDir | Out-Null

$Output = docker compose exec -T `
    -e "PRE_PROD_BRANCH=stable-15jun" `
    -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
    backend python -m app.cli.pre_prod_fx_seed `
        --run-id $RunId `
        --branch stable-15jun `
        --commit-sha $CommitSha `
        --start-date $StartDate `
        --end-date $EndDate

$ExitCode = $LASTEXITCODE
[System.IO.File]::WriteAllText(
    (Resolve-Path $ArtifactDir).Path + "\fx-seed.json",
    ($Output -join [Environment]::NewLine),
    [System.Text.UTF8Encoding]::new($false)
)

if ($ExitCode -ne 0) {
    throw "Seed cambial falhou com exit code $ExitCode."
}
```

## Segunda execução para idempotência

Execute novamente no mesmo commit e com o mesmo intervalo, usando outro `run_id` e outro diretório:

```powershell
$SecondRunId = Get-Date -Format "yyyyMMdd-HHmmss"
$SecondArtifactDir = "artifacts/pre-prod-fx-seed/$SecondRunId"

New-Item -ItemType Directory -Force -Path $SecondArtifactDir | Out-Null

$SecondOutput = docker compose exec -T `
    -e "PRE_PROD_BRANCH=stable-15jun" `
    -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
    backend python -m app.cli.pre_prod_fx_seed `
        --run-id $SecondRunId `
        --branch stable-15jun `
        --commit-sha $CommitSha `
        --start-date $StartDate `
        --end-date $EndDate

$SecondExitCode = $LASTEXITCODE
[System.IO.File]::WriteAllText(
    (Resolve-Path $SecondArtifactDir).Path + "\fx-seed.json",
    ($SecondOutput -join [Environment]::NewLine),
    [System.Text.UTF8Encoding]::new($false)
)

if ($SecondExitCode -ne 0) {
    throw "Segunda execução cambial falhou com exit code $SecondExitCode."
}
```

## Critérios de sucesso

Cada evidência deve apresentar:

- `schema_version = pre-prod-fx-seed.v1`;
- `branch = stable-15jun`;
- `commit_sha` igual ao `HEAD` executado;
- `source = BCB`;
- `rate_type = PTAX_SELL`;
- `ok = true`;
- `errors = []`;
- `after.duplicate_rows = 0`;
- `after.unsupported_pairs = []`;
- par `USD-BRL` presente;
- cobertura temporal dentro da janela solicitada.

Para a segunda execução, o estado final deve permanecer estável. O campo `imported` representa linhas submetidas ao UPSERT, não necessariamente novas linhas físicas.

## Evidência operacional validada

Em 28/07/2026, a Issue #217 foi concluída com duas execuções reais no PostgreSQL, ambas no commit `37c1d800be6f21dfc5c91b332a6ebe8748c0ac1c` e no intervalo `2026-07-20` a `2026-07-24`.

### Primeira execução

- `run_id`: `20260728-103750`;
- `before.total_rows`: 2;
- `after.total_rows`: 6;
- `imported.USD-BRL`: 5;
- quatro novas linhas físicas e um UPSERT sobre `2026-07-24` já existente;
- linha preexistente de `2026-07-25` preservada fora da janela;
- zero duplicidades;
- zero pares não suportados;
- `ok=true`.

### Segunda execução

- `run_id`: `20260728-104238`;
- `before.total_rows`: 6;
- `after.total_rows`: 6;
- `imported.USD-BRL`: 5;
- cobertura final estável de `2026-07-20` a `2026-07-25`;
- zero novas linhas físicas;
- zero duplicidades;
- zero pares não suportados;
- `ok=true`.

Conclusão: a idempotência operacional do seed cambial foi comprovada no mesmo SHA e intervalo.

## Critérios de aborto

Interromper e registrar na Issue operacional quando ocorrer qualquer um dos seguintes:

- branch ou SHA divergente;
- intervalo inválido;
- resposta PTAX vazia;
- resposta com data duplicada;
- linha fora da janela solicitada;
- par diferente de `USD-BRL`;
- duplicidade persistida em `fx_rates`;
- par não suportado persistido;
- exit code diferente de zero;
- `ok=false`;
- falha de conexão, autenticação ou advisory lock;
- resposta HTTP 400 causada por opção OData não suportada.

Não inserir taxa manual, fallback fixo, AwesomeAPI ou BRAPI para contornar o ensaio.

## Códigos de saída

- `0`: sucesso;
- `1`: falha operacional ou resultado inválido;
- `2`: outra execução mantém o advisory lock;
- `3`: falha inesperada, com mensagem sensível redigida.

## Evidências a registrar

Na Issue operacional, registrar:

- commit executado;
- `run_id` das duas execuções;
- intervalo solicitado;
- caminho dos dois JSONs;
- exit codes;
- `before` e `after` de cada execução;
- contagem `imported`;
- confirmação de zero duplicidades e zero pares não suportados;
- conclusão objetiva sobre idempotência.

## Fronteira arquitetural

Este estágio usa exclusivamente o cliente estrito `bcb_ptax_strict` e a persistência canônica em `fx_rates`. O serviço legado `fx_service` ainda possui cache e fallbacks para consumidores de aplicação, mas essas rotas não participam do seed auditável. A remoção ou endurecimento desse legado deve ocorrer em bloco separado, com análise de impacto sobre consumidores existentes.
