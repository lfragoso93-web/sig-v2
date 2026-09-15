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
