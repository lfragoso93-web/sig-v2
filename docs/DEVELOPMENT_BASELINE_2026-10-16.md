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

## Runtime local observado

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
Na consulta read-only de readiness assistida feita nesta rodada, o container
permaneceu saudável, mas a CLI não concluiu nem produziu relatório antes do
timeout. Uma tentativa local também não pôde resolver o hostname Docker `db`.
Portanto, não há resultado assistido atual confirmado; a evidência histórica de
`GO_ASSISTED` não deve ser reutilizada como estado atual.

## Validação do checkout observado

No checkout montado em modo somente leitura em container isolado, passaram 112
testes focados de eventos corporativos, projeção temporal e migrations. Após
ajustar o scanner AST para aceitar BOM UTF-8, os testes focados do scanner e da
migration passaram (5 testes), e o Architecture Doctor estático passou nos seis
checks catalogados. A suite backend completa foi reexecutada em 17/10/2026: 2.401 passaram, 5 foram skipped e zero falharam, em container descartavel com rede desativada e todo o checkout montado somente leitura. Flake8 e mypy passaram (411 arquivos); o Architecture Doctor passou (6/6). O fresh migration gate aplicou a cadeia completa num PostgreSQL 16 em tmpfs e `app.governance.alembic_drift_gate` passou, com head `20261016_corp_ev_effective_date`.

A persistencia agora rejeita linhas BRAPI/Yahoo concorrentes; as fixtures refletem B3 para ativos listados; e os scanners AST leem fontes com BOM. O contrato documental do seed foi alinhado a autoridade B3. Essa evidencia valida o checkout local, mas nao forma SHA reproduzivel nem certifica a imagem ativa.

## Baseline de certificação

A promoção persistida de 06/10/2026 é evidência histórica de outra identidade.
Não há neste baseline novo backup `pre-prod-backup.v3`, identidade derivada do
dataset, restore isolado, proof de certificação ou dry-run #384 para o runtime
observado. Não promover nem converter o estado assistido em autorização para
dados reais. Uma nova certificação exige SHA estável, dataset validado,
migrations aplicadas, gates requeridos, dry-run e uma decisão explícita para a
confirmação exata que ele emitir.

## Mapa de trabalho

1. Estabilizar e revisar as mudanças locais; resolver a cadeia de migrations e
   produzir um SHA candidato limpo sem incluir os arquivos temporários.
2. Atualizar esta baseline e os documentos vivos a partir do candidato final.
3. Executar os gates de código/documentação e o Architecture Doctor aplicáveis.
4. Criar backup v3 fresco, derivar dataset identity e validar restore isolado.
5. Construir a imagem candidata, preservar os volumes e fazer deploy controlado.
6. Conferir identidade, migrations, `/health`, `/ready`, readiness assistida e
   prova de restart.
7. Rodar o dry-run de certificação #384; só executar a confirmação exata após
   revisar a saída do plano.
8. Confirmar CodeQL pós-correção (#408), restore administrativo isolado (#83)
   e GOV-07 (#293); só então selecionar a próxima entrega de produto.

Qualquer alteração que mude SHA, schema, ambiente ou dataset exige repetir a
validação correspondente. Preserve PostgreSQL e seus volumes; nunca use
`down -v`, prune de volumes ou reutilize um backup antigo como identidade atual.
