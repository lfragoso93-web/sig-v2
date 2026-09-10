# 2026-09-10 - Gate de readiness para testes assistidos

## Adicionado

- Relatorio read-only `user-test-readiness.v1`.
- CLI `python -m app.cli.user_test_readiness`.
- Rota SuperAdmin `/api/v1/admin/bootstrap/user-test-readiness`.
- Testes focados para garantir que o relatorio permanece read-only e nao promove `ready_for_real_data`.

## Evidencia runtime

- `/health=200`;
- `/ready=503`;
- `go_for_assisted_user_tests=true`;
- `ready_for_real_data=false`;
- `blockers=[]`;
- `warnings=[]`.

## GOV-01 — readiness assistido

#303 foi rebaselined para o estado real da certificacao sintetica/assistida, separando `GO_ASSISTED` de abertura ampla com dados reais.

## GOV-02 — gates de dados reais

#226, #216, #158 e #227 foram reavaliadas contra as evidencias assistidas publicadas. A cadeia real ficou formalizada como #226 -> #216 -> #158 -> #227, preservando evidencias ja certificadas e evitando repeticao destrutiva por checklist historico.

## GOV-03 — operacao e OCI — CONCLUIDO

A fronteira operacional foi rebaselined:

- desenvolvimento, correcoes e certificacao pesada acontecem localmente;
- OCI e ambiente de homologacao de SHA ja certificado localmente;
- deploy OCI fixa o SHA exato e `APP_COMMIT_SHA` deve corresponder ao checkout;
- falhas de codigo encontradas na OCI voltam para reproducao/correcao local e geram novo SHA;
- `/ready=503` e esperado enquanto `ready_for_real_data=false`, mesmo com `/health=200` e `GO_ASSISTED`;
- readiness nao e forcado para aprovar smoke;
- restore/importacao real ampla, seeds globais e contracoes destrutivas permanecem subordinados aos gates reais;
- `docs/deployment/oci-execution-index.md`, `oci-first-deploy-runbook.md`, `oci.md`, `BOOTSTRAP_DATA_FLOW.md` e `USER_TEST_READINESS_GATE.md` foram alinhados ao mesmo contrato.

## GOV-04 — backlog funcional — CONCLUIDO

Backlog funcional reclassificado contra o estado real publicado:

- #58 — parcialmente implementada; detalhe de ativo, historico, Proventos e preco medio ja existem, restando consolidacao de cobertura, DY, metadados/iconografia e responsividade;
- #90 — refinamento de Patrimonio planejado, subordinado ao design system da #351;
- #149 — parcialmente implementada; Tesouro/RF atuais continuam corretos no escopo certificado, mas TWR diario dedicado permanece divida explicita;
- #246 — parcialmente implementada; Metas recebeu correcoes runtime-safe necessarias, enquanto o macroprojeto Metas + Analise permanece futuro;
- #351 — epic UX pos-GO, com bugs funcionais pequenos tratados separadamente;
- #352 — candidato P1 se o seletor de classe ainda impedir/errar lancamentos;
- #353 — P2 por padrao;
- #354 — candidato P1 se o mismatch de senha ainda afetar onboarding;
- #355–#359 — features pos-GO;
- #360 — Analysis Engine deterministico planejado apos #246;
- #361 — IA explicavel planejada e bloqueada por #360/#246.

Decisao de release: apenas findings reproduziveis que bloqueiem onboarding, lancamentos ou outra jornada critica devem atrasar `PORTFOLIO-TEST-READY`. Redesign, exportacao, import B3 avancado, calculadoras, Analysis Engine e IA nao sao blockers automaticos do primeiro GO.

Nenhuma funcionalidade, schema ou dado runtime foi alterado por GOV-04; as alteracoes foram de Issue/governanca e este registro documental.