# 2026-09-10 - Gate de readiness para testes assistidos

## Adicionado

- Relatorio read-only `user-test-readiness.v1`.
- CLI `python -m app.cli.user_test_readiness`.
- Rota SuperAdmin `/api/v1/admin/bootstrap/user-test-readiness`.
- Testes focados para garantir que o relatorio permanece read-only e nao promove `ready_for_real_data`.

## Documentacao

- `docs/USER_VALIDATION_RUNBOOK.md` atualizado com o novo status `GO_ASSISTED`.
- `docs/USER_TEST_READINESS_GATE.md` criado como contrato operacional do gate.
- Issue #303 rebaselined para refletir a certificacao sintetica/assistida ja comprovada.
- Gates reais #226, #216, #158 e #227 reavaliados em 10/09/2026 contra as evidencias assistidas publicadas.

## Evidencia runtime

- `/health=200`;
- `/ready=503`;
- `go_for_assisted_user_tests=true`;
- `ready_for_real_data=false`;
- `blockers=[]`;
- `warnings=[]`.

## Rebaseline dos gates de dados reais

A validacao assistida acrescentou evidencia real-controlada importante, sem promover o sistema para uso real amplo:

- Proventos portfolio-scoped: carteira 15, 49 ativos elegiveis, 183 eventos globais materializados na janela controlada e prova de idempotencia sem escrita fisica na segunda execucao;
- carteira assistida: CSV com 308 transacoes e 65 ativos distintos, seguido de reparos de cobertura e rebuild canonico;
- snapshots: 493 snapshots reconstruidos entre 22/10/2024 e 10/09/2026, com datas parciais/estimadas explicitamente marcadas;
- eventos corporativos: 122 eventos globais obtidos no escopo da carteira, ainda `PENDENTE/UNRECONCILED` para reconciliacao canonica;
- IRPF suportado e Renda Fixa/Tesouro validados em runtime assistido.

Essas evidencias mudam o estado de governanca, mas nao equivalem ao gate global originalmente exigido pela #226. A cadeia real permanece:

1. #226 — decidir e executar a estrategia final de Proventos para cobertura global/operacional, preservando a evidencia portfolio-scoped ja aprovada;
2. #216 — reconciliar benchmarks, cambio e Proventos no gate agregado;
3. #158 — executar a janela operacional final de importacao/rebuild/reconciliacao, sem repetir destrutivamente etapas ja certificadas;
4. #227 — produzir GO/NO-GO formal e somente entao avaliar `ready_for_real_data=true`.

O estado `GO_ASSISTED` continua separado de `ready_for_real_data`.

## Governanca

O rebaseline documental foi dividido em commits pequenos. Nenhum codigo, schema ou dado de runtime foi alterado por estes commits.