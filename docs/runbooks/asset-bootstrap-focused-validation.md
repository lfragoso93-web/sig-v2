# Validação focada do bootstrap canônico de ativos

Este roteiro valida somente contratos, planejamento, comparação offline e execução por fixtures. Ele não executa seed real, providers externos, migrations ou escrita financeira.

## Pré-condições

- branch `stable-15jun` sincronizada;
- working tree limpa;
- Docker Desktop disponível;
- ambiente virtual local ativo;
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

O runner descobre dinamicamente todos os arquivos `tests/test_asset_bootstrap*.py` existentes na imagem.

```powershell
docker compose run --rm backend `
  python scripts/run_asset_bootstrap_focused_checks.py
```

## 4. Lint e verificação de diff

A imagem final do backend não contém `ruff` ou ferramentas de instalação por desenho de segurança. Execute o linter pelo ambiente virtual local ou delegue esse gate à CI.

```powershell
python -m ruff check backend/app backend/tests backend/scripts

git diff --check
```

Se o projeto estiver usando o gate Flake8 canônico no ambiente local, execute o comando equivalente configurado no repositório em vez de instalar ferramentas dentro da imagem final.

## 5. Gerar dois planos read-only

Os artefatos são gravados no host em `backend/artifacts/asset-bootstrap`. Um novo `docker compose run` não enxerga automaticamente arquivos criados no host depois do build, pois o serviço não possui bind mount desse diretório.

```powershell
$RunId1 = "asset-bootstrap-plan-1"
$RunId2 = "asset-bootstrap-plan-2"

New-Item -ItemType Directory -Force backend/artifacts/asset-bootstrap | Out-Null

docker compose run --rm backend `
  python -m app.cli.plan_asset_bootstrap PETR4 ACAO `
    --run-id $RunId1 `
    --branch stable-15jun `
    --commit-sha $CommitSha `
  | Out-File -Encoding utf8 backend/artifacts/asset-bootstrap/plan-1.json

docker compose run --rm backend `
  python -m app.cli.plan_asset_bootstrap PETR4 ACAO `
    --run-id $RunId2 `
    --branch stable-15jun `
    --commit-sha $CommitSha `
  | Out-File -Encoding utf8 backend/artifacts/asset-bootstrap/plan-2.json
```

## 6. Comparar os artefatos offline no host

A comparação deve ser executada no host, dentro de `backend`, onde os dois arquivos existem. A identidade muda entre os planos, mas o comparador funcional ignora `run_id`, branch e commit SHA.

```powershell
Push-Location backend
try {
  python -m app.cli.compare_asset_bootstrap_reports `
    artifacts/asset-bootstrap/plan-1.json `
    artifacts/asset-bootstrap/plan-2.json
}
finally {
  Pop-Location
}
```

Resultado esperado:

```json
{
  "diff": {
    "equivalent": true,
    "changed_fields": [],
    "changed_capabilities": []
  },
  "offline": true,
  "read_only": true,
  "schema_version": "asset-bootstrap-report-diff.v1"
}
```

## Critérios de aprovação

- suíte focada aprovada;
- `compileall` aprovado;
- lint local ou CI aprovado;
- `git diff --check` aprovado;
- os cinco estágios aparecem como `planned` na CLI;
- comparação retorna `equivalent: true`;
- nenhum provider, banco, seed, migration ou rebuild é chamado.

## Proibições durante este roteiro

Não executar:

- seed real de ativos, preços, Proventos ou eventos corporativos;
- BRAPI ou Yahoo em modo operacional;
- migrations de contração;
- rebuild de pré-produção;
- importação de carteiras reais.
