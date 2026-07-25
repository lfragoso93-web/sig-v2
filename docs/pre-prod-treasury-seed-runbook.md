# Runbook — seed isolado do Tesouro Direto

## Objetivo

Executar exclusivamente o catálogo e o histórico oficial do Tesouro Direto por meio do contrato `pre-prod-treasury-seed.v1`, sem disparar B3/COTAHIST, benchmarks, câmbio, proventos, importação CSV, posições ou snapshots.

A implementação pertence à Issue #208 e ao estágio de rebuild controlado da Issue #158.

## Estado operacional

A CLI está implementada, mas sua presença no código **não autoriza execução na pré-produção real**. A primeira execução exige revisão do SHA promovido, banco alvo, janela operacional, fonte oficial e plano de preservação da evidência.

## Entrada oficial

```powershell
docker compose exec backend python -m app.cli.pre_prod_treasury_seed
```

Não use `sync_treasury_catalog_v2` e `rebuild_treasury_official_prices` separadamente para o estágio pré-produção. A CLI dedicada é a única entrada que coordena lock, transação, baseline, integridade, commit e rollback.

## Fluxo garantido

1. adquire advisory lock PostgreSQL dedicado;
2. captura baseline de ativos, aliases, preços, órfãos, duplicidades e legado;
3. executa catálogo oficial com `commit=False`;
4. executa histórico oficial com `commit=False`;
5. executa `flush` e inspeção final na mesma sessão;
6. confirma somente quando catálogo, histórico e integridade estão reconciliados;
7. executa rollback integral diante de erro ou divergência;
8. libera o advisory lock;
9. publica JSON UTF-8 do contrato `pre-prod-treasury-seed.v1`.

## Critérios obrigatórios de sucesso

O JSON só pode retornar `ok=true` quando:

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
| `1` | falha operacional ou resultado não reconciliado |
| `2` | outra execução mantém o advisory lock |
| `3` | falha inesperada com mensagem sensível redigida |

## Evidência

Preserve a saída integral em arquivo sem editar o JSON:

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$EvidencePath = "artifacts/pre-prod-rebuild/treasury-$RunId.json"

docker compose exec backend python -m app.cli.pre_prod_treasury_seed |
    Tee-Object -FilePath $EvidencePath

$ExitCode = $LASTEXITCODE
```

Antes de aprovar o estágio, registre na Issue #208:

- branch e SHA executados;
- banco e ambiente identificados sem credenciais;
- exit code;
- contagens `before` e `after`;
- cobertura temporal;
- resultados de catálogo e histórico;
- confirmação de zero órfãos, duplicidades e legado;
- caminho e checksum do arquivo de evidência.

## Idempotência

Uma segunda execução controlada deve manter:

- zero ativos duplicados;
- zero aliases duplicados;
- zero preços duplicados;
- zero recriação dos IDs legados;
- crescimento apenas quando a fonte oficial contiver dados novos ou corrigidos.

A idempotência deve ser comprovada na Issue #208 antes de atualizar a Issue #158 e antes de avançar para benchmarks, câmbio ou proventos.

## Aborto

Interrompa o estágio e não avance quando:

- o lock não puder ser adquirido;
- a fonte oficial estiver incompleta ou indisponível;
- houver ativo não resolvido ou payload vazio;
- qualquer contador de integridade for diferente de zero;
- o JSON não estiver íntegro;
- o SHA executado divergir do SHA aprovado.

Não tente corrigir manualmente o banco durante a mesma janela. Preserve a evidência, atualize a Issue #208 e abra um novo bloco corretivo.
