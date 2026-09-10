# Gate de readiness para testes assistidos

Atualizado em 10/09/2026.

## Objetivo

O gate `user-test-readiness.v1` decide se o SGI v2 pode receber rodadas assistidas com usuarios convidados. Ele nao substitui `/ready` nem autoriza dados reais irrestritos. O ambiente continua `ready_for_real_data=false` ate a decisao formal dos gates #226, #216, #158 e #227.

## Execucao

- Docker: `docker-compose run --rm backend python -m app.cli.user_test_readiness`
- SuperAdmin: `GET /api/v1/admin/bootstrap/user-test-readiness`

O relatorio e read-only e publica `schema_version`, `go_for_assisted_user_tests`, `ready_for_real_data`, `status`, `checks`, `counts`, `blockers`, `warnings` e `safety`.

## Evidencia runtime — 10/09/2026

```text
schema_version=user-test-readiness.v1
status=GO_ASSISTED
go_for_assisted_user_tests=true
ready_for_real_data=false
blockers=[]
warnings=[]
users=6
portfolios=5
transactions=332
assets=3684
asset_prices=4404638
portfolio_snapshots=536
asset_dividends=184
corporate_events=123
goals=2
```

## Interpretacao

`GO_ASSISTED` permite testes acompanhados com usuarios convidados, massa controlada e observacao tecnica. A validacao assistida ja produziu evidencia real-controlada de Proventos escopados por carteira, CSV seguido de rebuild/reconciliacao, reparos de historico, Tesouro, Renda Fixa, IRPF, snapshots e eventos corporativos portfolio-scoped.

Essas evidencias podem ser reutilizadas pelos gates reais quando seus contratos permitirem; nao devem ser descartadas nem repetidas apenas para satisfazer checklists historicos. `GO_ASSISTED` nao permite abertura ampla, seed global fora de janela autorizada ou promocao manual de readiness.

## Mapa canonico dos gates reais

- **#226 — Proventos:** prova portfolio-scoped esta comprovada e idempotente; permanece a estrategia/evidencia operacional para cobertura real global. A prova assistida e evidencia parcial valida, nao substituto automatico do gate global.
- **#216 — gate agregado:** benchmarks e cambio estao consolidados; Proventos e o ultimo componente material a reconciliar.
- **#158 — rebuild pre-producao:** preparacao, backup, limpeza historica e grande parte do rebuild ja possuem evidencia. Executar apenas o delta necessario: importacao candidata, rebuild/reconciliacao final, validacao funcional e eventual contracao fisica autorizada.
- **#227 — GO/NO-GO:** decisao formal de liberacao ampla, consumindo #303/#226/#216/#158 mais seguranca, resiliencia e homologacao.

Os corpos de #226/#216/#158/#227 sao os trackers vivos de execucao; este documento registra a fronteira entre eles e o gate assistido.

## Condicoes remanescentes

1. concluir rodada assistida sem blocker P0/P1 e congelar SHA candidato;
2. concluir estrategia operacional de Proventos na #226 aproveitando a evidencia portfolio-scoped;
3. reconciliar e concluir #216;
4. executar o delta final da #158 e reconciliar patrimonio, rentabilidade, Proventos, Tesouro, Renda Fixa e IRPF;
5. reconciliar eventos corporativos necessarios e definir tratamento dos eventos complexos `UNRECONCILED`;
6. repetir gates aplicaveis de seguranca/resiliencia sobre o mesmo SHA;
7. produzir GO/NO-GO formal na #227;
8. homologar no OCI o mesmo SHA certificado;
9. somente depois avaliar `ready_for_real_data=true` e promocao estrutural para `main`.

A persistencia auditavel de DARF pago permanece divida fiscal de produto. O gate final deve decidir explicitamente se ela bloqueia o escopo de abertura pretendido; a marcacao local atual nao e persistencia fiscal definitiva.

## Baseline documental GOV-02

Este mapa foi revalidado com `stable-15jun` sem atividade concorrente do Codex. O GOV-02 altera somente governanca/documentacao; nao executa seeds, migrations, CSV, rebuilds nem muda flags de readiness. As evidencias runtime citadas sao evidencias previamente produzidas e preservadas, nao novas execucoes deste bloco.
