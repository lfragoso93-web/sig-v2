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

Desenvolvimento/certificacao pesada local; OCI como homologacao do SHA exato; `/ready=503` esperado enquanto `ready_for_real_data=false`.

## GOV-04 — backlog funcional — CONCLUIDO

- #58: parcialmente implementada;
- #149: parcialmente implementada, nao blocker automatico se fail-closed;
- #246: Metas basica operacional, macroprojeto definitivo ainda planejado;
- #351: epic pos-GO;
- #352/#354: candidatos P1 se reproduziveis;
- #353: P2 por padrao;
- #355–#361: backlog de evolucao pos-GO.

## GOV-05 — documentacao raiz — CONCLUIDO

README, ROADMAP, CHANGELOG, `docs/DEVELOPMENT_CONTINUITY.md`, `docs/architecture.md`, `docs/ISSUE_GOVERNANCE.md` e `docs/USER_TEST_READINESS_GATE.md` foram rebaselined para o estado real de 10/09/2026.

Correcoes principais:

- removidos baselines historicos tratados como instrucao corrente;
- removida a premissa obsoleta de que `goals` nao poderia receber correcao/migration;
- removida a obrigacao mecanica de duas execucoes globais de Proventos;
- #58 deixou de aparecer como apenas planejada;
- #150 deixou de aparecer como trabalho futuro;
- ordem de promocao alinhada para #303 -> #226 -> #216 -> #158 -> OCI exact-SHA -> #227;
- backlog pos-GO separado de blockers reais;
- hierarquia de Issues alinhada ao mesmo fluxo;
- historico detalhado permanece preservado no Git e nos changelogs datados.

Baseline final GOV-05 / inicio GOV-06: `c4c8f27de542103fc73ead30a1632bdcf22d6b73`.

Nenhum codigo, schema ou dado runtime foi alterado durante GOV-05.