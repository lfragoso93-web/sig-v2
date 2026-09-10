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

Microcommits principais GOV-03:

- `b39b8374a3b39fe324e54dbb8d1a356e54501c79` — execution index;
- `c6c4754d2b6d8332259fb84b26daaa5aca35a251` — exact-SHA deploy runbook;
- `b0e2c7903ac4672d141d0b8ef5d4a0cc09a1bb92` — bootstrap/promotion flow;
- `dc06693331fb743746c73264ee6d22d70f01bb81` — OCI operator contract;
- `40d1c919259db77766ed2dd13050eab59f5cb067` — readiness/OCI boundary;
- `8e125eee7ca2b566a75ba95d5803f12133390b28` — final readiness reference before this changelog closure.

Nenhum codigo, schema, recurso OCI ou dado de runtime foi alterado por GOV-03.