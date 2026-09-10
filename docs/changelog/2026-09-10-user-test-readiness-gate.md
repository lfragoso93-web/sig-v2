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

- #303 rebaselined para o estado real da certificacao sintetica/assistida;
- `GO_ASSISTED` separado explicitamente de abertura ampla com dados reais.

## GOV-02 — gates de dados reais

#226, #216, #158 e #227 foram reavaliadas contra as evidencias assistidas publicadas.

- Proventos portfolio-scoped: 49 ativos elegiveis, 183 eventos na janela controlada e prova de idempotencia sem escrita fisica na segunda execucao;
- carteira assistida: CSV com 308 transacoes e 65 ativos distintos, seguido de reparos e rebuild canonico;
- snapshots: 493 snapshots entre 22/10/2024 e 10/09/2026, com parcialidade/estimativa explicita quando aplicavel;
- eventos corporativos: 122 eventos obtidos no escopo da carteira, ainda com reconciliacao canonica pendente para eventos complexos;
- IRPF suportado e Renda Fixa/Tesouro validados em runtime assistido.

A cadeia real ficou formalizada como #226 -> #216 -> #158 -> #227, preservando evidencias ja certificadas e evitando repeticao destrutiva por checklist historico.

## GOV-03 — operacao e OCI

A fronteira operacional foi rebaselined:

- desenvolvimento, correcoes e certificacao pesada acontecem localmente;
- OCI e ambiente de homologacao de SHA ja certificado localmente;
- deploy OCI deve fixar o SHA exato, e `APP_COMMIT_SHA` deve corresponder ao checkout;
- falhas de codigo encontradas na OCI voltam para reproducao/correcao local e geram novo SHA;
- `/ready=503` e esperado enquanto `ready_for_real_data=false`, mesmo com `/health=200` e `GO_ASSISTED`;
- readiness nao deve ser forcado para aprovar smoke;
- restore/importacao real ampla, seeds globais e contracoes destrutivas permanecem subordinados a #226/#216/#158/#227;
- `docs/deployment/oci-execution-index.md`, `oci-first-deploy-runbook.md`, `oci.md` e `BOOTSTRAP_DATA_FLOW.md` foram alinhados a esse contrato.

## Governanca

Os rebaselines documentais foram divididos em commits pequenos. Nenhum codigo, schema ou dado de runtime foi alterado por estes commits.