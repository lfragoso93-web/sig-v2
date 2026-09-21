# Checklist executavel — promotion reconciliation #158

## Objetivo

Executar a menor reconciliation necessaria para preparar o SHA/dataset candidato
ao primeiro GO, consumindo evidencias ja certificadas e sem repetir operacoes
destrutivas por checklist historico.

## Baseline obrigatorio

Antes de qualquer comando operacional:

1. `git fetch origin`;
2. `git switch stable-15jun`;
3. `git pull --ff-only origin stable-15jun`;
4. registrar branch, HEAD local, `origin/stable-15jun`, working tree e diff para
   `origin/main`;
5. confirmar que #303, #226 e #216 estao fechadas;
6. confirmar que #158 contem o SHA/dataset alvo do bloco;
7. manter `ready_for_real_data=false`.

## Evidencias consumidas

- #303: `PORTFOLIO-TEST-READY` aprovado.
- #226: Proventos portfolio-scoped/idempotente aceito como suficiente para
  promocao controlada.
- #216: benchmarks/cambio consolidados e gate agregado fechado.
- #363: gates tecnicos recuperados.

Nao repetir essas evidencias sem finding material novo.

## Entradas minimas

Registrar na #158 antes da execucao:

- SHA candidato;
- dataset/carteira alvo;
- janela de dados;
- artefatos existentes que serao consumidos;
- caminho local do artefato `pre-prod-backup.v3` ou justificativa explicita
  para dataset sintetico/controlado;
- comandos exatos a executar;
- comandos explicitamente proibidos no bloco;
- criterio de sucesso;
- criterio de abort.

## Dataset candidato

Antes de qualquer import/rebuild da #158, o ambiente local precisa conter um
dataset candidato aprovado.

Fontes aceitas:

- restore de `pre-prod-backup.v3` validado, com `backup-report.json`,
  `database.dump`, `database.dump.sha256` e `origin-inventory.json`;
- dataset sintetico/controlado explicitamente aprovado para repetir uma
  evidencia #303, sem ser tratado como dataset real de promocao.

NO-GO:

- banco com apenas schema e sem usuarios/carteiras/transacoes;
- artefato de backup parcial;
- dump sem `backup-report.json`;
- backup v1/v2;
- restaurar por fora do runbook sem registrar origem, SHA e checksum;
- executar migrations destrutivas sobre dataset com dados sem backup/gate
  explicito.

### Artefato candidato gerado em 14/09/2026

O artefato local abaixo passou na validacao estrutural, mas nao esta liberado
para restore porque a verificacao posterior encontrou runtime
`APP_COMMIT_SHA=unknown` no container de origem:

- caminho host:
  `C:\Users\Acer\Documents\Codex\sgi-v2-backups\20260914-233314`;
- `schema_version=pre-prod-backup.v3`;
- `run_id=20260914-233314`;
- branch `stable-15jun`;
- commit `1e7c3fca6e6acaea19a75c1197f036a1f1021199`;
- `consistent_snapshot=true`;
- `database.dump` com 40.977.216 bytes;
- SHA-256
  `486d971f25e7924249fac2c8b2630e59b746e16aeaa93bc5dc963093d9e33b81`;
- inventario de origem `pre-prod-inventory.v2`: 20 tabelas, 4.434.193 linhas,
  0 tabelas sem classificacao e 0 findings bloqueantes;
- validador local `scripts\oci_backup_artifact_check.ps1`: aprovado.

Esse artefato deve ser tratado como evidencia diagnostica, nao como entrada
aprovada para restore. O backup candidato precisa ser regenerado em runtime cujo
`APP_COMMIT_SHA` corresponda exatamente ao SHA informado na CLI. Import, rebuild,
cleanup, migration destrutiva e promocao de `ready_for_real_data=true`
continuam bloqueados.

### Artefato candidato aceito em 14/09/2026

O artefato local abaixo foi gerado a partir da imagem backend construida no SHA
certificado e com `APP_COMMIT_SHA` validado pela CLI:

- caminho host:
  `artifacts\pre-prod-rebuild\20260915-002119`;
- `schema_version=pre-prod-backup.v3`;
- `run_id=20260915-002119`;
- branch `stable-15jun`;
- commit `48b5041ceaf3240384065c42578fde6689ce17db`;
- `consistent_snapshot=true`;
- `pg_dump_major=16`;
- `server_major=16`;
- `database.dump` com 40.981.404 bytes;
- SHA-256
  `d42efc2f507854b58ab30429530aee10462c3b41ad29467db57ab91dfe77b4c9`;
- inventario de origem `pre-prod-inventory.v2`: 20 tabelas, 4.434.818 linhas,
  0 tabelas sem classificacao e 0 findings bloqueantes;
- validador local `scripts\oci_backup_artifact_check.ps1`: aprovado.

Esse artefato autoriza somente o proximo passo de restore em banco PostgreSQL
isolado/descartavel para reconciliation. Ele nao autoriza import, rebuild,
cleanup, migration destrutiva ou promocao de `ready_for_real_data=true`.

### Restore isolado aprovado em 14/09/2026

O artefato `20260915-002119` foi restaurado em banco PostgreSQL isolado:

- destino: `sig-v2-db-1:5432/sgi_restore_20260915_002119`;
- `restore-report.json`: `schema_version=pre-prod-restore.v1`, `ok=true`;
- `reconciliation-report.json`: `schema_version=pre-prod-reconciliation.v1`,
  `ok=true`;
- migrations de origem e destino:
  `20260906_rate_source32`, `20260910_goals_runtime`;
- tabelas ausentes: 0;
- tabelas inesperadas: 0;
- divergencias de classificacao: 0;
- divergencias de contagem: 0;
- divergencias de findings: 0;
- seguranca: `source_database_writes_executed=0`,
  `restore_target_only=true`, `cleanup_executed=false`,
  `rebuild_executed=false`.

Esse restore aprova somente a integridade do backup em laboratorio descartavel.
Ele nao autoriza import, rebuild, cleanup real, migration destrutiva ou promocao
de `ready_for_real_data=true`.

### Validacao read-only aprovada com deltas em 14/09/2026

O banco isolado `sgi_restore_20260915_002119` passou nos gates read-only:

- `pre-prod-inventory.v2`: 20 tabelas, 4.434.818 linhas, 0 tabelas sem
  classificacao, 0 findings bloqueantes;
- `user-test-readiness.v1`: `GO_ASSISTED`, sem blockers ou warnings,
  `ready_for_real_data=false`;
- seguranca: `read_only=true`, `writes_executed=0`,
  `promotes_ready_for_real_data=false`.

Dataset observado:

- 6 carteiras, 7 usuarios e 366 transacoes;
- carteira 15: 354 transacoes entre 22/10/2024 e 13/09/2026;
- carteira 13: 11 transacoes sinteticas entre 02/01/2026 e 20/02/2026;
- carteira 17: 1 transacao de cripto em 09/09/2026;
- snapshots consolidados: 608;
- snapshots por classe: 5.121;
- `asset_dividends`: 184 eventos globais;
- `corporate_events`: 123 eventos.

Deltas materiais para a #158:

- eventos corporativos: 123 eventos permanecem
  `UNRECONCILED/requires_review`, sendo 122 `PENDENTE` e 1 `APLICADO`;
- snapshots: existem dias com `has_partial_prices=true` e
  `return_is_estimated=true` nas carteiras 13, 15 e 17; isso deve permanecer
  explicito e nao pode virar zero/fallback silencioso;
- Tesouro: ha pares legado/canonico com quantidades liquidas opostas ou
  complementares em `transactions`; evidencia registrada tambem na #365 para
  impedir normalizacao destrutiva antes de #364;
- IRPF: nao ha tabelas fisicas `irpf*` no schema restaurado; validacao deve
  continuar usando os servicos runtime suportados, sem recriar tabelas legadas.

Proximo passo permitido: reconciliation read-only focada nos deltas materiais
acima, especialmente eventos corporativos materiais e consistencia de Tesouro,
sem import, rebuild, cleanup real, migration destrutiva ou seed global.

### Reconciliation read-only focada em 15/09/2026

O bloco focado confirmou a materialidade dos eventos corporativos e reduziu o
escopo operacional que ainda precisa de decisao:

- eventos corporativos globais pendentes: 122;
- todos os 122 pertencem a tickers presentes na carteira 15;
- eventos globais dentro da janela de exposicao da carteira 15: 14;
- evento de carteira ja aplicado, mas ainda `UNRECONCILED`: 1
  `TICKER_CHANGE` de `PETZ3` em 05/01/2026;
- total de eventos materiais para decisao da #158: 15, em 8 tickers
  (`AMOB3`, `FIQE3`, `GOAU4`, `ITSA4`, `KLBN11`, `KLBN4`, `PETZ3`, `POMO4`);
- `POMO4` mantem posicao liquida aberta de 30 unidades; os demais tickers
  materiais estao zerados no ledger, mas podem afetar historico/custo/IRPF;
- auditoria Tesouro read-only retornou 152 ativos, 151 grupos canonicos,
  0 duplicidades, 0 candidatos de migracao, `destructive_changes=false`;
- IRPF runtime da carteira 15 retornou contrato `irpf-annual-assessment.v1`
  para 2025 e 2026 sem tabelas fisicas legadas.

Decisao: #158 nao deve executar cleanup/rebuild/import ainda. O proximo bloco
deve decidir os 15 eventos corporativos materiais: reconciliar de forma
read-only se ja estiverem refletidos no ledger/snapshots ou abrir Issue
especifica para tratar o delta antes do GO.

### Decisao de eventos corporativos em 15/09/2026

O bloco de decisao cruzou os 15 eventos inicialmente materiais com a exposicao
real da carteira 15 na data de cada evento.

Resultado:

- todos os 15 eventos permanecem `UNRECONCILED/requires_review=true` e, pelo
  contrato atual de `corporate_action_position_reader`, ficam fora da projecao
  financeira;
- 4 eventos ocorreram com quantidade positiva na data do evento e bloqueiam o
  GO ate reconciliacao ou descarte formal:
  - `AMOB3` `BONIFICACAO` em 28/05/2025, quantidade 6;
  - `AMOB3` `GRUPAMENTO` em 29/05/2025, quantidade 6;
  - `KLBN11` `BONIFICACAO` em 17/12/2025, quantidade 10;
  - `KLBN11` `DESDOBRAMENTO` em 18/12/2025, quantidade 10;
- os outros 11 eventos revisados ocorreram com quantidade zero na data do
  evento;
- `POMO4` tem posicao final de 30 unidades, mas seus eventos de dezembro/2025
  ocorreram apos zeragem em 24/06/2025 e antes das recompras de abril/2026;
  portanto nao afetam a posicao aberta atual pelo projetor canonico.

Issue criada: #370. A #158 nao deve avancar para #269/#284/#227 nem abrir PR
estrutural para `main` enquanto #370 nao estiver reconciliada ou formalmente
aceita como nao bloqueante com evidencia.

### Simulacao read-only de impacto da #370 em 15/09/2026

Os 4 eventos bloqueantes foram simulados no motor puro
`project_position_timeline`, sem marcar eventos como reconciliados e sem
alterar o banco.

Resultado:

- `AMOB3` sem eventos: quantidade final 0, custo final 0, realizado -4,20;
- `AMOB3` aplicando os dois eventos pendentes: quantidade final 0, custo final
  0, realizado -86,966880;
- `KLBN11` sem eventos: quantidade final 0, custo final 0, realizado 1,70;
- `KLBN11` aplicando os dois eventos pendentes: quantidade final 0,2010,
  custo final 3,6511420448975590628369768 e realizado
  5,3511420448975590628369768.

Decisao: a #370 nao pode ser resolvida por promocao mecanica de eventos
`UNRECONCILED` para `MATCHED`. E necessario reconciliar economicamente fonte,
fator, data efetiva e tratamento de fracao/residuo antes de qualquer rebuild
seletivo. Enquanto isso, os eventos permanecem fail-closed e fora das projecoes.

### Classificacao tecnica da #370 em 15/09/2026

Foi feita leitura read-only dos metadados brutos dos 4 eventos bloqueantes:

- `AMOB3` BRAPI trazia `label=GRUPAMENTO`, `completeFactor="1 para 50"` e
  fator `0.02`, mas o normalizador havia persistido o evento como
  `BONIFICACAO`;
- `AMOB3` Yahoo trazia `GRUPAMENTO` com o mesmo fator `0.02` no dia seguinte;
- `KLBN11` BRAPI trazia `BONIFICACAO`, `completeFactor="1,01 para 1"` e fator
  `1.01`;
- `KLBN11` Yahoo trazia `DESDOBRAMENTO` com fator `1.01` no dia seguinte.

Correcao preventiva aplicada: o normalizador BRAPI agora respeita labels
explicitos `GRUPAMENTO` e `DESDOBRAMENTO` dentro de `stockDividends`, evitando
nova persistencia semanticamente errada como bonificacao. Essa correcao nao
migra eventos existentes nem altera projecoes ja persistidas.

Decisao operacional: `AMOB3` e `KLBN11` seguem dependentes de reconciliacao de
duplicidade economica entre fontes antes de qualquer evento ser marcado como
`MATCHED` ou usado em rebuild seletivo.

### Plano de reconciliacao economica da #370 em 15/09/2026

Foi feita simulacao read-only por fonte isolada no motor
`project_position_timeline`:

- `AMOB3` sem eventos: quantidade 0, custo 0, realizado -4,20;
- `AMOB3` com somente BRAPI corrigido para `GRUPAMENTO`: quantidade 0, custo 0,
  realizado -85,3440;
- `AMOB3` com somente Yahoo `GRUPAMENTO`: quantidade 0, custo 0, realizado
  -85,3440;
- `KLBN11` sem eventos: quantidade 0, custo 0, realizado 1,70;
- `KLBN11` com somente BRAPI `BONIFICACAO`: quantidade 0,10, custo
  1,8346534653465346534653465, realizado 3,5346534653465346534653465;
- `KLBN11` com somente Yahoo `DESDOBRAMENTO`: quantidade 0,10, custo
  1,8346534653465346534653465, realizado 3,5346534653465346534653465.

Decisao: nenhum dos 4 eventos deve ser marcado como `MATCHED` no dataset
candidato neste momento. O plano seguro e manter os eventos fora da projecao e
trata-los como conflito/revisao manual ate haver reconciliacao contra extrato
ou politica canonica de fracao/residuo.

Implicacao para #158: a existencia desses conflitos nao autoriza rebuild
seletivo e bloqueia o primeiro GO. Eventos corporativos materiais fazem parte do
lifecycle do investidor e precisam estar associados/reconciliados no banco antes
da promocao, ou formalmente resolvidos por politica canonica de conflito,
fracao/residuo e auditoria.

Decisao arquitetural: #370 permanece blocker de #158. Nao e valido tratar
eventos materiais apenas como nota externa ou como pendencia nao bloqueante do
primeiro GO controlado.

### Contrato minimo de reconciliacao da #370 em 15/09/2026

Foi criado um contrato puro, sem escrita em banco, para planejar a reconciliacao
dos eventos corporativos:

- `plan_conflict_reconciliation`: marca todas as evidencias do grupo como
  `CONFLICT`, `requires_review=true`, `is_canonical=false` e sem
  `matched_event_id`; nada entra na projecao financeira;
- `plan_matched_reconciliation`: exige um `canonical_event_id` explicito; somente
  esse evento fica `MATCHED`, `requires_review=false` e `is_canonical=true`;
  evidencias duplicadas ficam `CONFLICT`, revisaveis e apontam
  `matched_event_id` para o evento canonico.

O contrato nao executa SQL, nao muda eventos existentes, nao cria transacoes e
nao autoriza rebuild. Ele define o formato minimo seguro que um executor futuro
deve seguir para associar/reconciliar eventos materiais no banco.

### Dry-run auditavel da #370 em 15/09/2026

Foi criada a CLI read-only `corporate_event_reconciliation_dry_run`, que carrega
eventos por ID, aplica o contrato puro e sempre retorna
`database_writes_executed=0` em modo `dry_run=true`.

Execucoes no banco restaurado isolado:

- `AMOB3` eventos 12 e 13: plano `CONFLICT`, ambos `requires_review=true`,
  `is_canonical=false`, `matched_event_id=null`;
- `KLBN11` eventos 81 e 82: plano `CONFLICT`, ambos `requires_review=true`,
  `is_canonical=false`, `matched_event_id=null`.

Decisao: os planos confirmam que a proxima etapa pode ser um executor controlado
para persistir `CONFLICT` no banco restaurado, mas ainda nao autorizam
`MATCHED`, rebuild seletivo, nem promocao de GO.

### Persistencia controlada de `CONFLICT` em 15/09/2026

O executor foi habilitado apenas para `CONFLICT` mediante flag explicita
`--execute`. `MATCHED` permanece restrito a dry-run ate existir evidencia de
extrato, fracao/residuo e evento canonico.

Execucao no banco restaurado isolado:

- preflight: eventos 12, 13, 81 e 82 estavam `UNRECONCILED`,
  `requires_review=true`, `is_canonical=true`;
- `AMOB3` eventos 12 e 13: `corporate-event-reconciliation-execution.v1`,
  `database_writes_executed=2`, ambos `CONFLICT`, `requires_review=true`,
  `is_canonical=false`;
- `KLBN11` eventos 81 e 82: `corporate-event-reconciliation-execution.v1`,
  `database_writes_executed=2`, ambos `CONFLICT`, `requires_review=true`,
  `is_canonical=false`;
- pos-validacao SQL confirmou os 4 eventos em `CONFLICT`, com motivo de revisao
  registrado e sem `matched_event_id`.

Decisao: a persistencia do conflito formaliza o bloqueio, mas nao resolve #370
para GO. Os eventos seguem fora da projecao financeira ate reconciliacao contra
extrato ou politica canonica de fracao/residuo.

### Preflight read-only do ledger no dry-run

A CLI aceita `--ledger-preflight-event-id` somente sem `--execute`. O ID deve
estar entre os eventos informados e o resultado inclui o relatorio
`corporate-event-ledger-preflight.v1`, com `database_writes_executed=0` e
`ready_for_execution=false`.

Exemplo controlado:

```bash
python -m app.cli.corporate_event_reconciliation_dry_run \
  --decision CONFLICT \
  --event-id 12 --event-id 13 \
  --ledger-preflight-event-id 12 \
  --source-sha 0000000000000000000000000000000000000000 \
  --dataset-id fixture-amob3-2025 \
  --window-start 2025-01-01 --window-end 2025-12-31 \
  --reason "preflight read-only do ledger"
```

Esse comando apenas le as transacoes da carteira ate `effective_date`, calcula
a quantidade liquida projetada pelo `quantity_factor` e faz rollback da sessao.
Ele nao cria transacao, nao altera evento e nao autoriza `MATCHED`.

### Verificacao independente do artefato retido

Depois de reter `report.json` e `manifest.json`, a integridade pode ser
verificada sem abrir sessao de banco:

```bash
python -m app.cli.corporate_event_reconciliation_dry_run \
  --verify-report-file report.json \
  --verify-manifest-file manifest.json
```

O modo `verify` recalcula o SHA-256, confere o schema e exige
`dry_run=true` e `database_writes_executed=0`. Ele tambem confere se o
`artifact_context` do relatorio coincide exatamente com `dataset_id`, janela e
`source_commit_sha` do manifesto. Ele nao aceita argumentos de reconciliacao,
`--execute` ou escrita de novos artefatos.

### Pre-requisitos para saida de `CONFLICT` em 15/09/2026

Foi adicionado um contrato puro de evidencia para qualquer transicao futura para
`MATCHED`:

- referencia nao vazia de extrato/corretora e obrigatoria;
- `NO_FRACTIONAL_RESIDUE` so e valido quando nao houver quantidade fracionaria,
  preco de liquidacao ou tratamento de caixa;
- `CASH_SETTLEMENT` exige quantidade fracionaria, preco de liquidacao e
  tratamento de caixa explicitos;
- `MANUAL_REVIEW` nao autoriza `MATCHED`.

Esse contrato nao altera banco, nao executa rebuild e nao promove evento
corporativo. Ele apenas impede reconciliacao fail-open enquanto #370 nao tiver
evidencia operacional suficiente.

## Comandos permitidos por padrao

- consultas read-only de contagem, cobertura e integridade;
- importacao/rebuild estritamente necessario ao delta aprovado;
- invalidador/rebuild canonico de snapshots somente quando vinculado ao delta;
- verificacoes de restart, persistencia e idempotencia;
- testes locais dirigidos ao dominio reconciliado;
- `git diff --check`.

## Comandos proibidos sem gate explicito

- `full_market_rebuild` amplo como substituto da #158;
- seed global de Proventos sem finding material novo;
- seed global de mercado apenas para repetir evidencia historica;
- migration fisica/destrutiva sem backup, inventario e autorizacao registrados;
- contracao fisica de tabelas legadas fora de janela aprovada;
- hotfix direto na OCI;
- force push, reset destrutivo ou merge de `main` por conveniencia;
- qualquer alteracao que promova `ready_for_real_data=true`.

## Reconciliation minima

Validar e registrar:

1. lifecycle de transacoes;
2. patrimonio/resumo;
3. posicoes e custo medio;
4. snapshots consolidados e por classe;
5. rentabilidade;
6. Proventos sob demanda a partir de `asset_dividends`;
7. Tesouro;
8. Renda Fixa;
9. IRPF suportado;
10. eventos corporativos materiais ao dataset;
11. restart;
12. persistencia;
13. idempotencia;
14. provider-boundary no read path financeiro.

## Criterios de abort

Abortar o bloco e registrar Issue/finding se houver:

- divergencia monetaria nao explicada;
- ausencia convertida em zero/preco/cambio/retorno artificial;
- provider externo chamado em GET/read path financeiro;
- segunda fonte de verdade para posicao, saldo, Proventos ou eventos;
- migration drift ou Alembic/metadata drift bloqueante;
- writer paralelo de entidade canonica;
- evento corporativo material `UNRECONCILED` no dataset alvo;
- falha de restart/persistencia;
- idempotencia quebrada;
- Critical/High exploravel quando o bloco entrar no security gate.

## Evidencia minima de saida

Ao concluir o microbloco operacional, registrar na #158:

- SHA inicial e final;
- dataset e janela;
- comandos executados;
- contagens antes/depois;
- relatorio financeiro;
- resultado de restart/persistencia/idempotencia;
- testes locais e resultados reais;
- riscos e pendencias;
- decisao: aprovado, aprovado com ressalvas ou abortado.

## Proximo gate

Somente depois da #158 aprovada, executar #269 sobre exatamente o mesmo SHA
candidato.
