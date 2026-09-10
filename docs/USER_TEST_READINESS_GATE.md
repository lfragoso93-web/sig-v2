# Gate de readiness para testes assistidos

Atualizado em 10/09/2026.

## Objetivo

O gate `user-test-readiness.v1` decide se o SGI v2 pode receber rodadas assistidas com usuarios convidados. Ele nao substitui `/ready` nem autoriza dados reais irrestritos. O ambiente continua `ready_for_real_data=false` ate a decisao formal dos gates #226, #216, #158 e #227.

## Execucao

- Docker: `docker compose run --rm backend python -m app.cli.user_test_readiness`
- SuperAdmin: `GET /api/v1/admin/bootstrap/user-test-readiness`

## Evidencia registrada

Em 10/09/2026:

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
- **OCI:** homologacao do SHA exato ja certificado localmente.

OCI valida deploy, migrations, restart, persistencia, recursos, rede/tunnel e smoke. Nao e ambiente de desenvolvimento.

Durante a fase assistida, esta combinacao e valida:

```text
/health = 200
/ready = 503
GO_ASSISTED = true
ready_for_real_data = false
```

`/ready=503` nao deve ser contornado. Se OCI revelar defeito de codigo, a correcao volta ao ambiente local e gera novo SHA para nova homologacao.

Ver `docs/deployment/oci-execution-index.md`.

## Gates reais

### #226 — Proventos

O caminho portfolio-scoped esta comprovado e idempotente. Permanece a decisao operacional sobre portfolio-scoped versus global controlado para promocao.

### #216 — gate agregado

Benchmarks e cambio estao concluidos. Proventos e o componente material restante para reconciliacao agregada.

### #158 — promotion reconciliation

Preserva etapas destrutivas/estruturais ja certificadas e executa somente o delta operacional sobre SHA/dataset congelados: importacao quando necessaria, derivados canonicos, reconciliacao financeira, eventos corporativos materiais, restart/idempotencia e eventual contracao protegida.

### #227 — GO/NO-GO

Unica decisao formal de liberacao ampla. Consome #303, #226, #216, #158 e homologacao OCI do mesmo SHA antes de qualquer avaliacao de `ready_for_real_data=true`.

## Sequencia de promocao

1. concluir rodada assistida #303 sem blocker P0/P1 critico e congelar SHA;
2. fechar estrategia #226;
3. concluir #216;
4. executar delta #158;
5. homologar exatamente o SHA candidato na OCI;
6. produzir GO/NO-GO na #227;
7. somente depois avaliar `ready_for_real_data=true`.

## Governanca documental

GOV-01..05 alinharam Issues, readiness, OCI, backlog, README, ROADMAP, CHANGELOG, `docs/DEVELOPMENT_CONTINUITY.md`, `docs/architecture.md` e `docs/ISSUE_GOVERNANCE.md` ao estado atual.

Baseline documental para iniciar GOV-06: `57b1ffe44e0d289d5f046557e7683a565d120a5d`.

Baselines historicos permanecem no Git/changelogs datados, mas nao prevalecem sobre as Issues rebaselined e os documentos canonicos atuais.

A persistencia auditavel do estado de DARF pago e demais evolucoes fora do escopo inicial devem permanecer explicitas e nao ser confundidas com funcionalidades fiscais definitivas.