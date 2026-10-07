# Gate de readiness para testes assistidos

Atualizado em 06/10/2026.

## Objetivo

O gate `user-test-readiness.v1` decide se o SGI v2 pode receber rodadas
assistidas com usuarios convidados. Ele nao substitui `/ready` nem autoriza
dados reais irrestritos. #158, #269 e #227 foram fechadas e a PR #362 foi
promovida. A decisão explícita, persistente e auditável da #384 foi executada
posteriormente e mantém `ready_for_real_data=true` somente para a identidade
runtime certificada.

A implementacao da #384 ja existe (evento append-only, leitor DB-first,
identidade runtime, relatorio, executor, CLI e integracao com `/ready`) e uma
promocao real foi persistida em 06/10/2026. `GO_ASSISTED` nao foi reutilizado
como `status=GO`: a promoção usou evidência própria
`real-data-promotion-evidence.v1`.

## Execucao

- Docker: `docker compose run --rm backend python -m app.cli.user_test_readiness`
- SuperAdmin: `GET /api/v1/admin/bootstrap/user-test-readiness`

## Evidencia registrada

Em 10/09/2026, antes da promoção persistente da #384:

```text
schema_version=user-test-readiness.v1
status=GO_ASSISTED
go_for_assisted_user_tests=true
ready_for_real_data=false
blockers=[]
warnings=[]
```

Contagens observadas: users=6, portfolios=5, transactions=332, assets=3684, asset_prices=4404638, portfolio_snapshots=536, asset_dividends=184, corporate_events=123, goals=2.

## Interpretacao

`GO_ASSISTED` permite testes acompanhados com massa controlada. Nao permite abertura ampla, seed global real fora de gate, promocao manual de readiness nem tratar homologacao como declaracao fiscal/financeira final.

A validacao assistida ja produziu evidencia reutilizavel de CSV/rebuild, mercado, Tesouro, Renda Fixa, IRPF, Proventos portfolio-scoped idempotentes e eventos corporativos portfolio-scoped.

## Fronteira local x OCI

- **Local:** desenvolvimento, correcoes e certificacao pesada do SHA candidato.
- **OCI:** backlog futuro de infraestrutura/cloud (#284), fora do caminho atual.

Nao executar desenvolvimento, testes ou homologacao OCI na fase atual.

Durante a fase assistida anterior à promoção da #384, esta combinação era
válida e permanece como evidência histórica:

```text
/health = 200
/ready = 503
GO_ASSISTED = true
ready_for_real_data = false
```

`/ready=503` nao deve ser contornado. Promocao para `main` nao equivale a
autorizacao para dados reais.

No estado operacional certificado em 06/10/2026, `/ready=200` decorre
exclusivamente do evento DB-first válido e da correspondência exata entre
environment, branch, SHA, dataset e revision Alembic. O resultado
`GO_ASSISTED` continua separado e não promove nem revoga esse estado.

Ver `docs/deployment/oci-execution-index.md`.

## Evidencia historica dos gates concluidos

### #226 — Proventos

O caminho portfolio-scoped esta comprovado e idempotente. A decisao operacional de #226 aceita essa evidencia como suficiente para promocao controlada; global controlado fica condicionado a necessidade material nova em #216/#158.

### #216 — gate agregado

Fechado em 14/09/2026. Benchmarks e cambio estao concluidos, e a decisao de #226 foi consumida como evidencia suficiente de Proventos para promocao controlada. Nao repetir seed global por checklist historico.

### #158 — promotion reconciliation

Preserva etapas destrutivas/estruturais ja certificadas e executa somente o delta operacional sobre SHA/dataset congelados: importacao quando necessaria, derivados canonicos, reconciliacao financeira, eventos corporativos materiais, restart/idempotencia e eventual contracao protegida.

### #227 — GO/NO-GO (fechada)

A decisao arquitetural foi concluida e consumida pela PR #362. Ela nao promove
automaticamente `ready_for_real_data`.

## Sequencia vigente

1. preservar as evidencias historicas de #303, #226, #216, #158, #269 e #227;
2. executar desenvolvimento e gates no ambiente local canonico;
3. manter OCI/#284 como backlog futuro;
4. tratar eventual liberacao de dados reais exclusivamente pela #384.

Runbook: `docs/REAL_DATA_CERTIFICATION_RUNBOOK.md`.

## Governanca documental

GOV-01..05 alinharam Issues, readiness, OCI, backlog, README, ROADMAP, CHANGELOG, `docs/DEVELOPMENT_CONTINUITY.md`, `docs/architecture.md` e `docs/ISSUE_GOVERNANCE.md` ao estado atual.

Baseline documental para iniciar GOV-06: `57b1ffe44e0d289d5f046557e7683a565d120a5d`.

Baselines historicos permanecem no Git/changelogs datados, mas nao prevalecem sobre as Issues rebaselined e os documentos canonicos atuais.

A persistencia auditavel do estado de DARF pago e demais evolucoes fora do escopo inicial devem permanecer explicitas e nao ser confundidas com funcionalidades fiscais definitivas.
