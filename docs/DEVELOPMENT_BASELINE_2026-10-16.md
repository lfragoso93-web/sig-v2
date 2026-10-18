# Baseline de desenvolvimento e ambiente — 16/10/2026

Este registro separa o checkout Git, as mudanças locais e o runtime observado.
Ele não declara a certificação do runtime nem substitui os runbooks operacionais.

## Checkout e remoto

- Branch: `stable-15jun`.
- HEAD publicado: `b37661921e3a8455f45c8b676b28955d6ad3d0ea`.
- `origin/stable-15jun` local aponta para o mesmo SHA.
- Comparação GitHub ao vivo: `stable-15jun` está 7 commits à frente e 0 atrás
  de `main`; `main` está no SHA `4948b6b609ddf2e9a0ea51fbec0be4677f4f9985`.
- Não havia Pull Requests abertas na consulta de 16/10/2026.
- Antes desta rebaseline documental, o working tree continha 15 arquivos
  modificados e cinco itens não rastreados.
  As mudanças de código concentram-se em reconciliação de eventos corporativos,
  projeção temporal e apresentação de frações pendentes. Há uma migration nova
  de evidência efetiva e artefatos temporários de candidato. Esse conteúdo ainda
  não constitui uma identidade Git reproduzível. A rebaseline documental foi
  seguida por dois ajustes de cobertura de validação: contrato da migration nova
  e leitura UTF-8 com BOM pelo scanner do Doctor. Eles ainda não estão em um
  commit candidato.
- Os artefatos temporários não são parte da documentação versionada e devem ser
  preservados até identificar seus owners e finalidade.

## Issues

O inventário GitHub consultado encontrou 453 Issues no repositório: 23 abertas,
430 fechadas e nenhuma PR aberta. As abertas estão agrupadas assim:

- Gates e dados: #149, #370, #408.
- Backup, governança e schema: #83, #272, #293.
- OCI em backlog: #284.
- Providers e bootstrap: #127, #130, #253.
- UX, ativo e navegação: #58, #90, #351, #353.
- Renda Fixa e ferramentas: #355, #356, #357, #358, #359.
- Metas, análise e autenticação: #97, #246, #360, #361.

`docs/ISSUE_GOVERNANCE.md` mantém a classificação e a sequência recomendada.
Issues fechadas incluem entregas e rastreadores inválidos; não devem ser
reabertas sem evidência de regressão ou escopo restante.

## Documentação

O catálogo contém 137 Markdown em `docs/` e quatro skills versionadas. Esta
rebaseline atualizou os documentos vivos de status, arquitetura, governança,
readiness, operação, eventos corporativos e Proventos. Relatórios datados e
changelogs históricos foram preservados e identificados como fotografia de sua
data, não como descrição do runtime atual. Os documentos atualizados nesta
passada são `README.md`, `ROADMAP.md`, `CHANGELOG.md`,
`docs/DEVELOPMENT_BASELINE_2026-10-16.md`,
`docs/DEVELOPMENT_CONTINUITY.md`, `docs/ISSUE_GOVERNANCE.md`,
`docs/architecture.md`, `docs/USER_TEST_READINESS_GATE.md`,
`docs/USER_VALIDATION_RUNBOOK.md`, `docs/operations.md`,
`docs/REAL_DATA_CERTIFICATION_RUNBOOK.md`, `docs/CORPORATE_ACTIONS.md`,
`docs/CORPORATE_ACTIONS_IMPLEMENTATION_STATUS.md`,
`docs/PROVENTOS_ARCHITECTURAL_AUDIT.md` e
`docs/GOV_07_MAIN_DIVERGENCE_AUDIT_2026-09-11.md` e
`docs/BOOTSTRAP_DATA_FLOW.md`, `docs/PRE_PROD_REBUILD_RUNBOOK.md`,
`docs/BRAPI_V2_INVENTORY.md`, `docs/price-history.md`,
`docs/deployment/oci-execution-index.md` e `docs/deployment/oci.md`.

## Runtime local observado antes do candidato — 16/10/2026

Consulta read-only ao Docker Desktop em 16/10/2026:

- Backend `sig-v2-backend-1`: saudável, imagem
  `sig-v2-validation:b3-adapter-b3766192`.
- Banco PostgreSQL e Redis: saudáveis. Frontend e tunnel também estavam ativos.
- Digest observado do backend: `sha256:2b3ab9ef4f163522361dd809c1615dfdda8b55fa043884b32652b7ac1e78a334`.
- O frontend estava no digest
  `sha256:63de406724e9016a8d3e8ab1754d442937c5d079668e272065563e47084e82cd`,
  criado oito dias antes da consulta; não há prova de que inclua as alterações
  locais atuais.
- Alembic no banco: `20261016_corp_eff_null (head)`. A migration local que
  adiciona `effective_date` à evidência de reconciliação ainda não estava
  aplicada na observação inicial; o `entrypoint.sh` agora aponta para
  `20261016_corp_ev_effective_date` para executar essa migration no deploy
  candidato.
- `/health`: `status=ok`, PostgreSQL e Redis `ok`.
- `/ready`: HTTP 503; o relatório retornou `runtime_identity_error` e
  `ready_for_real_data=false`.
- Runtime declarado: `APP_BRANCH=stable-15jun`, `ENVIRONMENT=testing`;
  `APP_COMMIT_SHA` não corresponde ao HEAD do checkout nem a um objeto Git local;
  `REAL_DATASET_REFERENCE` está vazio.
- Bootstrap reportado: `not_started`, com sincronização automática desabilitada.

Portanto, o runtime está operacional para diagnóstico e seu gate de dados reais
está fechado. `/health=200` não certifica a identidade; `/ready=503` é o
comportamento fail-closed esperado para a identidade incompleta/divergente.
Na consulta feita antes do deploy candidato, a CLI não concluiu antes do
timeout. Esse resultado histórico não descreve o runtime atual; consulte a
observação de 17/10 abaixo.

## Validação do checkout observado

No checkout montado em modo somente leitura em container isolado, passaram 112
testes focados de eventos corporativos, projeção temporal e migrations. Após
ajustar o scanner AST para aceitar BOM UTF-8, os testes focados do scanner e da
migration passaram (5 testes), e o Architecture Doctor estático passou nos seis
checks catalogados. A suite backend completa foi reexecutada em 17/10/2026: 2.401 passaram, 5 foram skipped e zero falharam, em container descartavel com rede desativada e todo o checkout montado somente leitura. Flake8 e mypy passaram (411 arquivos); o Architecture Doctor passou (6/6). O fresh migration gate aplicou a cadeia completa num PostgreSQL 16 em tmpfs e `app.governance.alembic_drift_gate` passou, com head `20261016_corp_ev_effective_date`.

A persistencia agora rejeita linhas BRAPI/Yahoo concorrentes; as fixtures refletem B3 para ativos listados; e os scanners AST leem fontes com BOM. O contrato documental do seed foi alinhado a autoridade B3. Essa evidencia valida o checkout local, mas nao forma SHA reproduzivel nem certifica a imagem ativa.

## Baseline anterior de certificação

A promoção persistida de 06/10/2026 é evidência histórica de outra identidade.
Na fotografia pré-deploy não havia novo backup, restore, proof ou dry-run #384.
Essa cadeia foi executada para o candidato em 17/10 e está registrada abaixo.

## Runtime candidato implantado — 17/10/2026

- O SHA do runtime deve corresponder ao checkout de `stable-15jun`; o proof
  allowlisted em `artifacts/certification-proof/` registra a identidade completa
  do build vigente. Cada atualização desta documentação também altera o SHA e
  exige nova cadeia de backup, restore, proof e dry-run.
- Environment `production`, branch `stable-15jun`; `APP_COMMIT_SHA` corresponde
  ao checkout e `REAL_DATASET_REFERENCE` veio do backup `20261017-candidate-004433`.
- Imagens backend e frontend foram atualizadas. Os digests da imagem corrente
  ficam registrados no inventário operacional, fora deste baseline versionado.
- Alembic atual: `20261016_corp_ev_effective_date`. `/health=200`; PostgreSQL e
  Redis saudáveis. `user_test_readiness` retornou `GO_ASSISTED`, sem blockers,
  warnings ou escritas; totais: 8 usuários, 7 carteiras, 423 transações, 3.677
  ativos, 4.411.758 preços, 1.031 snapshots, 435 dividendos de ativos, 125
  eventos corporativos e 2 metas.
- `/ready=503` por `identity_mismatch` do evento anterior (#384), divergente em
  SHA, dataset e Alembic; permanece fail-closed até nova promoção.
- O backup v3 pós-migration e o restore isolado reconciliaram migrations,
  tabelas e contagens com `ok=true`, sem divergências. Os relatórios em
  `artifacts/pre-prod-rebuild/` vinculam o run ao SHA exato que os gerou; uma
  atualização posterior exige outro run.
- Backend: 2.401 passed, 5 skipped; Flake8, mypy (411 arquivos), Doctor 6/6,
  migration e drift gates passaram. Frontend: 171 testes, typecheck e lint
  passaram. O proof de certificação ficou `failed` apenas por
  `certification.not_certified`; o dry-run #384 gerou plano válido com zero
  escritas e sem commit. Uma atualização posterior invalida seu plano; a nova
  confirmação deve ser autorizada para a identidade atual e fica preservada em
  `artifacts/certification-proof/`.

## Mapa de trabalho

1. Consolidar esta atualização factual em novo SHA; repetir backup v3, restore,
   gates, Doctor, proof e dry-run #384, pois o SHA muda.
2. Revisar a confirmação exata do novo plano e executar somente após
   autorização explícita; então comprovar `/ready` e persistência após restart.
3. Confirmar CodeQL pós-correção (#408), restore administrativo isolado (#83)
   e GOV-07 (#293); só então selecionar a próxima entrega de produto.

Qualquer alteração que mude SHA, schema, ambiente ou dataset exige repetir a
validação correspondente. Preserve PostgreSQL e seus volumes; nunca use
`down -v`, prune de volumes ou reutilize um backup antigo como identidade atual.

## Atualizacao factual — 17/10/2026

O runtime foi consultado no Docker: backend healthy, imagem rotulada com o SHA `5c4ad3906475316294196a826ff140cb3e4bf950`, `ENVIRONMENT=production`, branch `stable-15jun`, dataset `pre-prod-backup.v3:sha256:7d97c52de9ae58ad457f3ffe25055a9963a6a0dea4c9690b8dc72f900fa7133e`, Alembic `20261016_corp_ev_effective_date` e `/ready=200` (`ready_for_real_data=true`, evento 6 persistido). A certificacao vale somente para essa identidade.

O checkout/runtime estao em `5c4ad3906475316294196a826ff140cb3e4bf950`; `origin/stable-15jun` local permanece em `b37661921e3a8455f45c8b676b28955d6ad3d0ea` (tres commits atras). O SHA remoto vivo nao foi confirmado e nenhum push foi feito. Quatro itens `.tmp-candidate-*` preexistentes foram preservados.

Issues #83, #293 e #408 foram consultadas ao vivo e permanecem abertas. A prova recente de #83 cobre backup/restore por funcoes de servico e reconciliacao estrutural em banco descartavel, mas nao autentica/audita/consulta status via API administrativa. #408 aguarda confirmacao CodeQL posterior as correcoes. GOV-07/#293 aguarda correlacao final do inventario integral. Esses status prevalecem sobre fotografias anteriores neste documento; os registros historicos permanecem preservados.

Qualquer novo SHA implantado exige novo backup v3, restore, proof, gates e dry-run vinculados a identidade nova. A promocao anterior certifica apenas `5c4ad390`.
## Resultado GOV-07 — atualizacao de 17/10/2026

O inventario vivo encontrou 22 Issues abertas e nenhuma PR aberta. #83 esta
fechada apos ensaio administrativo HTTP integrado. A correlacao do snapshot
local nao encontrou Issue aberta claramente duplicada ou sem destino. #353 tem
scroll restoration global e testes unitarios, mas ainda requer validacao
desktop/mobile. #293 segue aberta ate publicar/reconciliar a documentacao com a
ponta remota: o conector nao retornou o SHA de `stable-15jun`, e `git ls-remote`
falhou por rede. Consulte `docs/ISSUE_GOVERNANCE.md` para a classificacao.

## Atualizacao de execucao da #83 — 17/10/2026

Issue #83 foi fechada como concluida apos ensaio HTTP integrado em PostgreSQL descartavel. O ensaio cobriu autenticacao SuperAdmin, backup, download autenticado, restore para banco alvo vazio, auditoria, status persistido e integridade origem/alvo. A reconciliação estrutural complementar passou. Procedimento em `docs/ADMIN_BACKUP_RESTORE_REHEARSAL.md`; evidencias em `artifacts/admin-backup-restore/20261017-issue83/`. Bancos e rede efemeros foram removidos; Compose operacional segue healthy. A proxima sequencia e #408 (CodeQL) e depois GOV-07/#293.

## Ambiente de testes assistidos isolado — 17/10/2026

Foi criado e iniciado o projeto Compose `sgi-usertest`, sem modificar `sig-v2`.
As imagens backend/frontend correspondem ao checkout `5c4ad3906475316294196a826ff140cb3e4bf950`; PostgreSQL, Redis e backend estao healthy,
Alembic esta em `20261016_corp_ev_effective_date`, `/health=200` e frontend
`127.0.0.1:18080=200`. A porta 80 herdada inicialmente do Compose base foi
removida com `!override`, confirmando apenas publicacao em loopback. Os volumes
criados sao `sgi-usertest_postgres_data` e `sgi-usertest_usertest_artifacts`.

Identidade e configuracao: `ENVIRONMENT=testing`, branch `stable-15jun`, SHA do
checkout, dataset de dados reais vazio e tokens BRAPI/quotes vazios. `/ready=503`
com `runtime_identity_error` e esperado e mantem a politica real fail-closed;
esse gate nao e requisito dos testes assistidos isolados. A configuracao e os
digests estao em `docs/USER_TEST_STACK.md`. A rotina de atualizacao por nova
alteracao tambem esta documentada nesse runbook.
