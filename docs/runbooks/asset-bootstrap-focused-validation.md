# Validação focada do bootstrap canônico de ativos

Este roteiro valida somente contratos, planejamento, comparação offline e execução por fixtures. Ele não executa seed real, providers externos, migrations ou escrita financeira.

## Pré-condições

- branch `stable-15jun` sincronizada;
- working tree limpa;
- Docker Desktop disponível;
- Issue #227 ainda tratada como gate bloqueante para operações reais.

## 1. Sincronizar e confirmar o SHA

```powershell
git fetch origin
git switch stable-15jun
git pull --ff-only origin stable-15jun
git status --short
$CommitSha = (git rev-parse HEAD).Trim().ToLowerInvariant()
$CommitSha
```

## 2. Construir o backend

```powershell
docker compose build backend
```

## 3. Executar a suíte focada e compileall

```powershell
docker compose run --rm backend `
  python scripts/run_asset_bootstrap_focused_checks.py
```

## 4. Ruff e verificação de diff

```powershell
docker compose run --rm backend `
  ruff check app tests scripts

git diff --check
```

## 5. Gerar dois planos read-only

```powershell
$RunId1 = "asset-bootstrap-plan-1"
$RunId2 = "asset-bootstrap-plan-2"

New-Item -ItemType Directory -Force artifacts/asset-bootstrap | Out-Null

docker compose run --rm backend `
  python -m app.cli.plan_asset_bootstrap PETR4 ACAO `
    --run-id $RunId1 `
    --branch stable-15jun `
    --commit-sha $CommitSha `
  | Out-File -Encoding utf8 artifacts/asset-bootstrap/plan-1.json

docker compose run --rm backend `
  python -m app.cli.plan_asset_bootstrap PETR4 ACAO `
    --run-id $RunId2 `
    --branch stable-15jun `
    --commit-sha $CommitSha `
  | Out-File -Encoding utf8 artifacts/asset-bootstrap/plan-2.json
```

## 6. Comparar os artefatos offline

A identidade muda entre os dois planos; as capacidades e contagens devem permanecer estáveis.

```powershell
docker compose run --rm backend `
  python -m app.cli.compare_asset_bootstrap_reports `
    artifacts/asset-bootstrap/plan-1.json `
    artifacts/asset-bootstrap/plan-2.json
```

O comparador pode retornar divergência por causa de `run_id`. A revisão deve confirmar que não houve alteração em estados, capacidades ou contagens.

## Critérios de aprovação

- suíte focada aprovada;
- `compileall` aprovado;
- Ruff aprovado;
- `git diff --check` aprovado;
- os cinco estágios aparecem como `planned` na CLI;
- nenhum provider, banco, seed, migration ou rebuild é chamado;
- diferenças entre planos limitam-se à identidade auditável quando os inputs funcionais são iguais.

## Proibições durante este roteiro

Não executar:

- seed real de ativos, preços, Proventos ou eventos corporativos;
- BRAPI ou Yahoo em modo operacional;
- migrations de contração;
- rebuild de pré-produção;
- importação de carteiras reais.
