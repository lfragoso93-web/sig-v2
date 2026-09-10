# 2026-09-10 - Gate de readiness para testes assistidos

## Adicionado

- Relatorio read-only `user-test-readiness.v1`.
- CLI `python -m app.cli.user_test_readiness`.
- Rota SuperAdmin `/api/v1/admin/bootstrap/user-test-readiness`.
- Testes focados para garantir que o relatorio permanece read-only e nao
  promove `ready_for_real_data`.

## Estado consolidado

- `status=GO_ASSISTED` para validacao acompanhada;
- `go_for_assisted_user_tests=true`;
- `ready_for_real_data=false`;
- `blockers=[]`;
- `warnings=[]`;
- `/health=200` e `/ready=503` no ambiente de validacao registrado.

O resultado libera continuidade dos testes assistidos, mas nao equivale a
readiness de producao nem autoriza abertura ampla com dados reais.

## Evidencias correlacionadas

O rebaseline documental da #303 passou a registrar como ja certificados ou
validados no ciclo atual:

- fixture sintetica multiclasse e reconciliacao financeira independente;
- CSV dry-run/import/replay/invalidos/atomicidade/rebuild;
- snapshots canonicos com persistencia, replay, invalidacao e recomposicao;
- IRPF das classes suportadas;
- Redis fail-open e persistencia PostgreSQL apos restart;
- smoke UI e jornadas assistidas basicas;
- Proventos escopados por carteira com prova de idempotencia;
- fronteira explicita de TWR de Renda Fixa sob #149.

## Governanca

A Issue #303 deixou de refletir um checklist majoritariamente pendente e foi
atualizada para representar o estado real da certificacao em 10/09/2026.

O gate agora distingue explicitamente:

1. `PORTFOLIO-TEST-READY` / validacao assistida;
2. estrategia final de Proventos sob #226;
3. reconciliacao agregada #216;
4. importacao/rebuild operacional #158;
5. decisao final #227;
6. somente depois, eventual `ready_for_real_data=true`.

A execucao escopada de Proventos e suficiente para a carteira assistida, mas nao
fecha automaticamente o gate global de Proventos.

## Documentacao

- `docs/USER_VALIDATION_RUNBOOK.md` permanece como runbook das jornadas
  acompanhadas;
- `docs/USER_TEST_READINESS_GATE.md` foi rebaselined para explicitar a fronteira
  assistido x dados reais, Proventos escopados, TWR de Renda Fixa e criterios de
  bloqueio/continuidade;
- #303 foi sincronizada com as evidencias ja publicadas na `stable-15jun`.

## Baseline

Baseline observada no inicio do GOV-01:
`9644a643f70d9126c7d07bfbac9231320515ee40`.

Commit documental do rebaseline do gate:
`3f48c3128150fee6c5ea0b52da5f8a5bdf7064f7`.
