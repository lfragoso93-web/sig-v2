# Runbook de rebuild pré-produção — SGI v2

> Issue-mãe: #158  
> Backup e restauração isolada: #183  
> Executor e ensaio isolado: #196  
> Limpeza real controlada: #199  
> Seed isolado de proventos: #226  
> Última atualização: 28/07/2026

## Objetivo

Executar a primeira reconstrução limpa da base canônica de forma reversível, auditável e idempotente antes do go-live.

Este runbook trata da operação controlada de pré-produção. A futura interface administrativa de backup e restore permanece no escopo da Issue #83 e não deve duplicar os comandos ou regras definidos aqui.

## Estado atual

A cadeia técnica foi validada em PostgreSQL real e em banco descartável:

- inventário `pre-prod-inventory.v2`;
- backup consistente `pre-prod-backup.v3`;
- restauração isolada reconciliada;
- impacto `pre-prod-cleanup-impact.v2` em modo read-only;
- exportação `pre-prod-export.v1`;
- plano `pre-prod-cleanup-execution.v1` sem acesso ao banco;
- executor transacional com sucesso e rollback comprovados;
- perfil isolado `sgi-pre-prod-isolated`;
- perfil real `sgi-pre-prod-real`, validado localmente com 34 testes.

A execução real ainda não ocorreu. A cadeia `20260724-100752` foi invalidada operacionalmente pela mudança de código necessária para habilitar o perfil real. Após a promoção do novo código, todo o conjunto de artefatos deve ser regenerado com novo `run_id` e novo SHA.

## Princípios obrigatórios

- Nenhuma limpeza sem backup validado e restauração emergencial disponível.
- Nenhuma operação destrutiva antes de dry-run, exportação e plano aprovados.
- Branch, SHA e `run_id` devem coincidir em toda a cadeia.
- Usuários, autenticação, configurações, auditoria e dados fiscais não são removidos.
- Transações, renda fixa e eventos corporativos devem ser exportados e validados antes da limpeza.
- Dados reconstruíveis devem ser recriados exclusivamente pelos pipelines canônicos.
- Cada etapa deve produzir contagens, checksums, duração, estado final e ativos não resolvidos.
- Uma falha interrompe a sequência; etapas posteriores não podem mascarar erro anterior.
- Seeds, coleta, importação e rebuild não podem ocorrer durante a transação de limpeza.
- Cada seed posterior usa contrato, lock, transação, evidência e reconciliação próprios.
- O seed de proventos segue `pre-prod-dividends-seed.v1`: leitura limitada a `assets`, `transactions`, `portfolios`, `asset_dividends` e `dividends`; escrita limitada a `asset_dividends` e `dividends`.
- Nenhum artefato pode ser editado manualmente ou sobrescrito.

## Política oficial de classificação

A fonte executável da política é `TABLE_POLICIES`, em `pre_prod_inventory_service.py`. Cada tabela recebe classificação e justificativa no relatório `pre-prod-inventory.v2`.

O inventário real validado contém 24 tabelas: 11 preservadas, 3 exportáveis e 10 reconstruíveis.

### Preservar — 11 tabelas

- `alembic_version`;
- `audit_logs`;
- `goal_allocations`;
- `goals`;
- `irpf_losses`;
- `irpf_records`;
- `irpf_reports`;
- `portfolio_class_targets`;
- `portfolios`;
- `system_configs`;
- `users`.

Essas tabelas contêm estrutura aplicada, identidade, configuração, preferências, trilha de auditoria ou histórico fiscal não integralmente regenerável.

### Exportar antes de qualquer limpeza — 3 tabelas

- `corporate_events`;
- `fixed_income_investments`;
- `transactions`.

Eventos corporativos podem conter estado aplicado e dados brutos; renda fixa contém condições contratuais; transações formam o livro-razão financeiro. Nenhuma delas pode ser perdida ou presumida como regenerável.

### Reconstruir — 10 tabelas

- `asset_aliases`;
- `asset_dividends`;
- `asset_prices`;
- `assets`;
- `dividends`;
- `fx_rates`;
- `portfolio_class_snapshots`;
- `portfolio_positions`;
- `portfolio_snapshots`;
- `rate_history`.

Essas tabelas possuem fonte oficial, pipeline idempotente ou são projeções derivadas dos dados preservados/exportados.

`app_configs` e `dividends_sync_jobs` não pertencem ao inventário canônico atual e não devem ser inseridas manualmente na política escrita.

Qualquer tabela nova ou desconhecida permanece `unclassified`, faz a CLI retornar código diferente de zero e exige revisão arquitetural antes da limpeza.

## Artefatos obrigatórios

Criar uma pasta por execução:

```text
artifacts/pre-prod-rebuild/YYYYMMDD-HHMMSS/
```

Ela deve conter, conforme a etapa:

- `database.dump` em formato custom;
- `database.dump.sha256`;
- `database.contents.txt`;
- `pg-client-version.txt` e `source-server-version.txt`;
- `backup-report.json` no contrato `pre-prod-backup.v3`;
- `origin-inventory.json`;
- `cleanup-impact.json`;
- `export/manifest.json`;
- `export/tables/corporate_events.csv`;
- `export/tables/fixed_income_investments.csv`;
- `export/tables/transactions.csv`;
- `cleanup/plan.json`;
- `cleanup/execution.json`;
- `cleanup/preserved-before.json`;
- `cleanup/preserved-after.json`;
- `cleanup/post-cleanup-inventory.json`;
- `cleanup/reconciliation.json`;
- logs e evidências das etapas posteriores de seed, importação e rebuild.

Esses artefatos não devem ser versionados no Git nem conter URLs completas, usuários, senhas ou segredos.

## Perfis autorizados da CLI

Entrada operacional:

```text
python -m app.cli.pre_prod_isolated_cleanup
```

A CLI aceita somente dois marcadores mutuamente exclusivos.

### Perfil isolado

```text
sgi-pre-prod-isolated
```

Exige que origem e destino tenham identidades normalizadas diferentes de host, porta e banco. É usado somente em banco descartável restaurado do backup.

### Perfil real

```text
sgi-pre-prod-real
```

Exige que `--source-database-url` e `--target-database-url` representem exatamente a mesma identidade normalizada de host, porta e banco. Isso impede que a autorização real seja reutilizada contra um destino diferente.

Qualquer outro marcador aborta antes da criação do engine e antes de qualquer escrita.

## Confirmação composta

Formato exato:

```text
CLEANUP <run-id> ON <database> AT <commit-sha> WITH <plan-sha256>
```

A confirmação deve ser recalculada a partir do plano canônico da execução atual. Autorizações anteriores não podem ser promovidas automaticamente para outro `run_id`, SHA, banco ou checksum.

## Sequência operacional

### 1. Congelar a referência

- confirmar branch `stable-15jun` sincronizada com a `main` promovida;
- registrar SHA completo executado;
- confirmar working tree limpa;
- confirmar migrations aplicadas e árvore Alembic com um único head;
- revisar Issues e PRs abertas, inclusive Dependabot;
- impedir importações, coleta, seeds, rebuilds e uso concorrente durante a janela;
- definir responsável, início, critério de cancelamento e restauração emergencial.

### 2. Gerar e validar backup

```powershell
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$CommitSha = (git rev-parse HEAD).Trim()

docker compose exec `
  -e "PRE_PROD_BRANCH=stable-15jun" `
  -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
  backend python -m app.cli.pre_prod_backup --run-id $RunId
```

A validação mínima exige:

- major do `pg_dump` idêntico ao major do servidor PostgreSQL;
- inventário e dump vinculados ao mesmo snapshot, com `consistent_snapshot=true`;
- `pg_dump` concluído com código zero;
- arquivo custom não vazio;
- checksum SHA-256 registrado;
- conteúdo listado por `pg_restore --list`;
- confirmação de zero escritas na origem.

Backups `pre-prod-backup.v1` e `pre-prod-backup.v2` são recusados pelo restore.

### 3. Exportar as tabelas obrigatórias

```powershell
docker compose exec `
  -e "PRE_PROD_BRANCH=stable-15jun" `
  -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
  backend python -m app.cli.pre_prod_export --run-id $RunId
```

A exportação deve:

- usar snapshot read-only consistente;
- conter exatamente as três tabelas `export_before_cleanup`;
- registrar contagens, schema, bytes e SHA-256;
- retornar `reconciled=true`;
- bloquear a sequência diante de qualquer divergência.

### 4. Gerar impacto e plano

A exportação gera ou reconcilia `cleanup-impact.json`. Em seguida:

```powershell
docker compose exec `
  -e "PRE_PROD_BRANCH=stable-15jun" `
  -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
  backend python -m app.cli.pre_prod_cleanup_plan --run-id $RunId
```

O plano deve confirmar:

- `schema_version=pre-prod-cleanup-execution.v1`;
- `mode=plan`;
- `database_accessed=false` durante o planejamento;
- zero blockers e zero ciclos;
- checksums dos cinco artefatos de entrada;
- 13 tabelas no `cleanup_order`;
- zero escritas, limpeza ou rebuild;
- ausência de sobrescrita.

### 5. Aprovar ou abortar

Abortar se ocorrer qualquer uma das condições:

- branch, SHA ou `run_id` divergentes;
- backup não restaurável ou snapshot inconsistente;
- exportação incompleta ou não reconciliada;
- checksum divergente;
- tabela preservada classificada para limpeza;
- qualquer tabela `unclassified`;
- blockers ou ciclos;
- migrations pendentes;
- processos concorrentes;
- artefato alterado manualmente;
- indisponibilidade de restauração emergencial.

### 6. Registrar autorização explícita

Antes da execução real, registrar na Issue #199:

- `run_id`;
- branch;
- SHA completo;
- banco-alvo redigido;
- checksum canônico do plano;
- confirmação de janela isolada;
- confirmação composta exata.

### 7. Executar a limpeza real

Usar o mesmo URL PostgreSQL síncrono para origem e destino e o marcador `sgi-pre-prod-real`.

Usar o wrapper PowerShell oficial, preenchido somente após revisão dos valores:

```powershell
$PlanPath = "artifacts/pre-prod-rebuild/$RunId/cleanup/plan.json"
$PlanSha = '<sha256-canônico-do-plano>'
$DatabaseName = '<nome-do-banco>'
$Confirmation = "CLEANUP $RunId ON $DatabaseName AT $CommitSha WITH $PlanSha"

.\scripts\Invoke-PreProdRealCleanup.ps1 `
  -PlanPath $PlanPath `
  -CommitSha $CommitSha `
  -Confirmation $Confirmation

$CleanupExitCode = $LASTEXITCODE
```

Regras:

- definir previamente `PRE_PROD_SYNC_DATABASE_URL` com a URL PostgreSQL síncrona;
- usar somente o wrapper versionado para a execução real;
- não usar `--rehearsal-fail-after-table`;
- não executar DDL, `TRUNCATE`, `CASCADE` ou comandos paralelos;
- interromper imediatamente diante de exit code diferente de zero;
- não iniciar seed ou rebuild antes da reconciliação.

### 8. Reconciliar imediatamente

Confirmar nos artefatos:

- `final_state=committed`;
- `committed=true`;
- tabelas planejadas zeradas;
- tabelas preservadas inalteradas;
- `reconciliation.ok=true`;
- nenhum segredo persistido;
- nenhuma alteração de schema;
- nenhum seed, coleta, importação ou rebuild iniciado durante a limpeza.

### 9. Recriar dados canônicos em blocos separados

Ordem:

1. catálogo e aliases;
2. B3 COTAHIST;
3. Tesouro oficial;
4. benchmarks;
5. câmbio;
6. eventos e proventos pelo contrato `pre-prod-dividends-seed.v1`;
7. importação da carteira;
8. posições e custos médios;
9. snapshots consolidados e por classe;
10. auditoria final;

O estágio de proventos não pode reutilizar scheduler, endpoint em background, backfill pós-transação, asset seed, pipeline de mercado ou `full_market_rebuild`. Sua implementação deve obedecer à Issue #226 e ao contrato `docs/PRE_PROD_DIVIDENDS_SEED_CONTRACT.md`, com advisory lock dedicado, transação única, rollback integral, fontes explícitas e duas execuções controladas comparadas offline.

O primeiro estágio possui entrada dedicada e não dispara os demais:

```powershell
docker compose exec backend python -m app.cli.pre_prod_b3_seed `
  --start-year <ANO_INICIAL> `
  --end-year <ANO_FINAL> `
  --cutoff-date <AAAA-MM-DD>
```

O JSON deve ser preservado como evidência. Uma segunda execução controlada deve
retornar `catalog.created=0` e `cotahist.rows_inserted=0`, salvo mudança real na
fonte entre as execuções. Exit code `2` indica lock concorrente.

O comando operacional de rebuild existente é:

```powershell
docker compose exec backend python -m app.cli.full_market_rebuild
```

Ele não substitui backup, dry-run, exportação, plano ou limpeza controlada e não deve ser executado automaticamente no mesmo bloco.

## Relatório final mínimo

O relatório deve registrar:

- SHA da aplicação;
- início, fim e duração;
- contagens antes/depois por entidade;
- número de ativos, aliases, preços, proventos, transações e snapshots;
- ativos não resolvidos e motivo;
- divergência monetária entre posições e snapshots;
- cobertura por classe;
- resultado das telas Resumo, Patrimônio, Rentabilidade e Proventos;
- resultado do teste de reimportação CSV;
- decisão final: aprovado, aprovado com ressalvas ou abortado.

## Idempotência

Uma segunda execução, sem novos dados externos ou transações, deve:

- não criar duplicatas;
- não alterar identificadores canônicos sem justificativa;
- manter contagens estáveis, exceto fontes atualizadas;
- reconciliar os mesmos valores financeiros;
- produzir relatório comparável ao anterior.

## Estado operacional

- Issue #183: backup e restauração v3 concluídos.
- Issue #185: impacto read-only concluído.
- Issue #188 / PR #191: exportação concluída.
- Issue #195 / PR #194: plano concluído.
- Issue #196 / PR #198: executor e ensaio isolado concluídos.
- Issue #199: autorização e execução real em andamento.
- Cadeia `20260724-100752`: validada, mas não reutilizável após mudança do SHA.
- Issue #226: contrato inicial do seed isolado de proventos publicado; implementação e execução real pendentes.
- Próximo gate operacional de proventos: implementar envelope e inspeção read-only antes de qualquer persistência.
