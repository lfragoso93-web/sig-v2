# Operação — SGI v2

> Última atualização: 21/07/2026

Este guia descreve os comandos de manutenção, validação e diagnóstico do SGI v2.

---

## Subir o ambiente

```bash
cp .env.example .env
docker compose up -d --build
```

Ver logs do backend:

```bash
docker compose logs -f backend
```

---

## Inventário pré-produção read-only

Comando oficial:

```powershell
docker compose exec backend python -m app.cli.pre_prod_inventory
```

Salvar o JSON em UTF-8 no PowerShell 7+:

```powershell
$ReportFile = ".\pre-prod-inventory-$(Get-Date -Format 'yyyyMMdd-HHmmss').json"
docker compose exec backend python -m app.cli.pre_prod_inventory |
    Tee-Object -FilePath $ReportFile
```

O contrato atual é `pre-prod-inventory.v2`. Para aprovar o inventário, confirme:

- `unclassified_tables` igual a `0`;
- `blocking_findings` igual a `0`;
- `read_only` igual a `true`;
- `writes_executed` igual a `0`;
- justificativa presente em todas as tabelas.

O CLI retorna código diferente de zero quando existe achado bloqueador ou tabela desconhecida. Nenhuma limpeza ou rebuild é executada por esse comando.

---

## Backup validado e restauração isolada — Issue #183

Pré-requisitos:

- executar somente na branch `stable-15jun`;
- congelar importações e escritas concorrentes durante o ciclo;
- confirmar que o inventário v2 da origem não possui bloqueios;
- nunca reutilizar um banco de restauração;
- não executar limpeza nem rebuild neste bloco.

O backend persiste os artefatos em `./artifacts/pre-prod-rebuild/<run-id>/`.
No PowerShell:

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse stable-15jun).Trim()

docker compose exec `
    -e "PRE_PROD_BRANCH=stable-15jun" `
    -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
    backend python -m app.cli.pre_prod_backup --run-id $RunId
```

O contrato atual do backup é `pre-prod-backup.v3`. Backups v1 e v2 são
incompatíveis e devem permanecer apenas como evidência das execuções abortadas.
O v3 executa inventário e `pg_dump` no mesmo snapshot exportado em transação
`REPEATABLE READ READ ONLY`, mesmo quando tabelas reconstruíveis recebem novos dados.

O backup só termina com código zero quando:

- o major do `pg_dump` é igual ao major do servidor PostgreSQL;
- `pg_dump` gera um arquivo custom não vazio;
- `pg_restore --list` consegue inspecionar o dump;
- o checksum SHA-256 é registrado;
- o inventário da origem usa `pre-prod-inventory.v2` sem bloqueios;
- `consistent_snapshot=true`, comprovando que inventário e dump usam o mesmo estado lógico;
- branch e SHA completo estão registrados;
- nenhuma escrita é executada na origem.

Crie um banco vazio e exclusivo para a restauração. O exemplo abaixo usa o mesmo
cluster PostgreSQL, mas um banco logicamente isolado:

```powershell
$DbUser = (docker compose exec -T db printenv POSTGRES_USER).Trim()
$DbPassword = (docker compose exec -T db printenv POSTGRES_PASSWORD).Trim()
$RestoreDb = "sgi_restore_$($RunId -replace '-', '_')"

docker compose exec db createdb --username $DbUser $RestoreDb

$EscapedUser = [uri]::EscapeDataString($DbUser)
$EscapedPassword = [uri]::EscapeDataString($DbPassword)
$RestoreUrl = "postgresql://$EscapedUser`:$EscapedPassword@db:5432/$RestoreDb"
$ArtifactDir = "/app/artifacts/pre-prod-rebuild/$RunId"

docker compose exec `
    -e "PRE_PROD_RESTORE_DATABASE_URL=$RestoreUrl" `
    backend python -m app.cli.pre_prod_restore `
    $ArtifactDir --confirm-isolated-target
```

Uma execução abortada não deve reutilizar o dump, o `run_id` nem o banco
isolado. Gere um novo backup v3 e um novo banco.

O restore é recusado quando o destino coincide com a origem, usa o mesmo nome de
banco, contém qualquer tabela ou diverge do checksum. A aplicação usa
`pg_restore --single-transaction --exit-on-error`.

Aprovar somente quando `reconciliation-report.json` apresentar:

- `ok=true`;
- contratos de origem e restauração iguais a `pre-prod-inventory.v2`;
- migrations idênticas;
- nenhuma tabela ausente ou inesperada;
- nenhuma divergência de classificação, contagem ou achado;
- zero tabelas não classificadas e zero achados bloqueantes;
- `source_database_writes_executed=0`;
- `cleanup_executed=false` e `rebuild_executed=false`.

Não remova o banco isolado nem altere a origem até os artefatos serem revisados e
anexados à Issue #183.

---

## Rebuild completo de mercado

Comando oficial:

```bash
python -m app.cli.full_market_rebuild
```

Via Docker Compose:

```bash
docker compose exec backend python -m app.cli.full_market_rebuild
```

PowerShell com arquivo de log:

```powershell
$LogFile = ".\full-market-rebuild-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

docker compose exec backend python -m app.cli.full_market_rebuild 2>&1 |
    Tee-Object -FilePath $LogFile
```

---

## O que o rebuild executa

1. Reconciliar catálogo de ativos.
2. Auditar cobertura histórica de preços.
3. Sincronizar lacunas reais.
4. Atualizar Tesouro Direto.
5. Atualizar benchmarks.
6. Sincronizar e materializar proventos.
7. Reconstruir snapshots TWR.
8. Gerar auditoria final de cobertura.

---

## Leitura do resultado

Resultado esperado:

```json
{
  "ok": true,
  "steps": [
    {"name": "catalog_and_asset_prices", "ok": true},
    {"name": "treasury", "ok": true},
    {"name": "benchmarks", "ok": true},
    {"name": "proventos", "ok": true},
    {"name": "twr_snapshots", "ok": true},
    {"name": "final_coverage_audit", "ok": true}
  ]
}
```

Se uma etapa retorna `errors`, `assets_failed` ou lista de erros, o rebuild deve terminar com `ok=false`, mesmo que as demais etapas concluam.

---

## Sinais saudáveis

Durante uma execução saudável:

- não há `QueuePool limit reached`;
- snapshots TWR terminam em segundos ou poucos minutos;
- proventos materializam sem erro de limite de parâmetros;
- preços inválidos são rejeitados antes do banco;
- lacunas antigas já esgotadas não são repetidas;
- chamadas externas diminuem em execuções subsequentes.

---

## Sinais de atenção

| Sinal | Interpretação |
|---|---|
| `NumericValueOutOfRangeError` | Preço anômalo passou pela validação |
| `number of query arguments cannot exceed 32767` | Alguma materialização voltou a usar lote grande demais |
| `QueuePool limit reached` | Sessões longas ou concorrência excessiva |
| Muitos `startDate=1900-01-01` | Histórico máximo não está sendo usado ou smart sync não persistiu estado |
| Muitos fallbacks lentos | Roteador ainda está tentando fonte incompatível |
| `has_partial_prices=true` persistente | Cobertura de preços insuficiente ou classe sem roteamento correto |

---

## Validação depois de mudanças estruturais

1. Rebuild da imagem:

```bash
docker compose up -d --build backend
```

2. Executar manutenção:

```bash
docker compose exec backend python -m app.cli.full_market_rebuild
```

3. Conferir logs:

```bash
docker compose logs -f --since 10m backend
```

4. Validar no frontend:

- Resumo;
- Patrimônio;
- Rentabilidade;
- Proventos;
- importação CSV.

---

## Scheduler

A rotina diária deve respeitar a ordem:

```text
sincronizar dados
        ↓
materializar proventos
        ↓
reconstruir snapshots
        ↓
servir KPIs
```

Se os horários forem alterados, preserve a dependência lógica.

---

## Quando rodar `full_market_rebuild`

- Após importação CSV grande.
- Após mudança estrutural no cálculo de rentabilidade.
- Após migration de dados canônicos.
- Após correção de provedor ou histórico de preços.
- Antes de validar Resumo, Patrimônio e Rentabilidade.
- Antes de abrir PR estrutural para `main`.

---

## Observação sobre PowerShell

O CLI de inventário configura `stdout` e `stderr` em UTF-8. Em terminais antigos, execute antes:

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [Console]::OutputEncoding
```

O PowerShell pode exibir `NativeCommandError` quando o processo escreve em `stderr`, mesmo sem falha real. A fonte de verdade é o JSON final e o código de saída do comando.
