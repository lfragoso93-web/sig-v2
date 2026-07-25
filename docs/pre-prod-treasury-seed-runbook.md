# Runbook — seed isolado do Tesouro Direto

## Objetivo

Executar exclusivamente o catálogo e o histórico oficial do Tesouro Direto por meio do contrato `pre-prod-treasury-seed.v1`, sem disparar B3/COTAHIST, benchmarks, câmbio, proventos, importação CSV, posições ou snapshots.

A implementação pertence à Issue #208 e ao estágio de rebuild controlado da Issue #158.

## Estado operacional

A CLI está implementada, mas sua presença no código **não autoriza execução na pré-produção real**. A primeira execução exige revisão do SHA promovido, banco alvo, janela operacional, fonte oficial e plano de preservação da evidência.

## Identidade operacional obrigatória

Toda execução deve informar e publicar no JSON final:

- `run_id` no formato `YYYYMMDD-HHMMSS`;
- branch exatamente `stable-15jun`;
- `commit_sha` Git completo, hexadecimal minúsculo, com 40 caracteres.

A CLI valida os três valores antes de abrir qualquer sessão de banco. Identidade inválida retorna código operacional `1` e não inicia catálogo, histórico ou inspeção.

## Entrada oficial

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse HEAD).Trim()

docker compose exec backend python -m app.cli.pre_prod_treasury_seed `
    --run-id $RunId `
    --branch stable-15jun `
    --commit-sha $CommitSha
```

Não use `sync_treasury_catalog_v2` e `rebuild_treasury_official_prices` separadamente para o estágio pré-produção. A CLI dedicada é a única entrada que coordena identidade, lock, transação, baseline, integridade, commit e rollback.

## Fluxo garantido

1. valida `run_id`, branch e SHA antes do banco;
2. adquire advisory lock PostgreSQL dedicado;
3. captura baseline de ativos, aliases, preços, órfãos, duplicidades e legado;
4. executa catálogo oficial com `commit=False`;
5. executa histórico oficial com `commit=False`;
6. executa `flush` e inspeção final na mesma sessão;
7. confirma somente quando catálogo, histórico e integridade estão reconciliados;
8. executa rollback integral diante de erro ou divergência;
9. libera o advisory lock;
10. publica JSON UTF-8 do contrato `pre-prod-treasury-seed.v1`.

## Critérios obrigatórios de sucesso

O JSON só pode retornar `ok=true` quando:

- a identidade publicada corresponde ao comando executado;
- `catalog.errors=0`;
- `history.unresolved_assets` está vazio;
- `history.empty_payloads=0`;
- `after.orphan_prices=0`;
- `after.duplicate_prices=0`;
- `after.legacy_assets=0`;
- `after.legacy_prices=0`;
- os ativos canônicos permanecem e os IDs legados `4742` e `4747` não reaparecem.

## Exit codes

| Código | Significado |
|---:|---|
| `0` | estágio concluído e reconciliado |
| `1` | identidade inválida, falha operacional ou resultado não reconciliado |
| `2` | outra execução mantém o advisory lock |
| `3` | falha inesperada com mensagem sensível redigida |

## Evidência

Preserve a saída integral em arquivo sem editar o JSON:

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse HEAD).Trim()
$EvidencePath = "artifacts/pre-prod-rebuild/treasury-$RunId.json"

docker compose exec backend python -m app.cli.pre_prod_treasury_seed `
    --run-id $RunId `
    --branch stable-15jun `
    --commit-sha $CommitSha |
    Tee-Object -FilePath $EvidencePath

$ExitCode = $LASTEXITCODE
```

Antes de aprovar o estágio, registre na Issue #208:

- `run_id`, branch e SHA publicados no JSON;
- banco e ambiente identificados sem credenciais;
- exit code;
- contagens `before` e `after`;
- cobertura temporal;
- resultados de catálogo e histórico;
- confirmação de zero órfãos, duplicidades e legado;
- caminho e checksum do arquivo de evidência.

## Idempotência

Uma segunda execução controlada, com novo `run_id` e o mesmo SHA promovido, deve manter:

- zero ativos duplicados;
- zero aliases duplicados;
- zero preços duplicados;
- zero recriação dos IDs legados;
- o baseline da segunda execução igual ao estado final da primeira;
- as contagens finais e a cobertura temporal estáveis.

Preserve as duas evidências em arquivos distintos e execute o comparador offline:

```powershell
$FirstEvidence = "artifacts/pre-prod-rebuild/treasury-<RUN_ID_1>.json"
$SecondEvidence = "artifacts/pre-prod-rebuild/treasury-<RUN_ID_2>.json"

python -m app.cli.pre_prod_treasury_seed_idempotency `
    --first $FirstEvidence `
    --second $SecondEvidence |
    Tee-Object -FilePath "artifacts/pre-prod-rebuild/treasury-idempotency.json"

$IdempotencyExitCode = $LASTEXITCODE
```

O relatório usa o contrato `pre-prod-treasury-seed-idempotency.v1` e retorna:

| Código | Significado |
|---:|---|
| `0` | idempotência comprovada |
| `1` | evidências válidas, mas divergentes |
| `2` | arquivo ausente, JSON inválido ou contrato incompatível |

A comparação exige `run_id` distintos, mesma branch, mesmo `commit_sha`, encadeamento do baseline e estabilidade de estado e cobertura. O comparador não acessa banco, rede ou variáveis de ambiente.

A idempotência deve ser comprovada na Issue #208 antes de atualizar a Issue #158 e antes de avançar para benchmarks, câmbio ou proventos.

## Aborto

Interrompa o estágio e não avance quando:

- a identidade for inválida ou divergir do SHA aprovado;
- o lock não puder ser adquirido;
- a fonte oficial estiver incompleta ou indisponível;
- houver ativo não resolvido ou payload vazio;
- qualquer contador de integridade for diferente de zero;
- o JSON não estiver íntegro;
- o comparador offline retornar código diferente de `0`.

Não tente corrigir manualmente o banco durante a mesma janela. Preserve a evidência, atualize a Issue #208 e abra um novo bloco corretivo.
