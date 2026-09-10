# Gate de readiness para testes assistidos

Atualizado em 10/09/2026.

## Objetivo

O gate `user-test-readiness.v1` consolida sinais operacionais para decidir se o SGI v2 pode receber rodadas assistidas com usuarios convidados. Ele nao substitui `/ready` e nao autoriza dados reais irrestritos. O ambiente continua `ready_for_real_data=false` ate a decisao formal dos gates #226, #216, #158 e #227.

## Execucao e contrato

No Docker: `docker-compose run --rm backend python -m app.cli.user_test_readiness`.

Como SuperAdmin: `GET /api/v1/admin/bootstrap/user-test-readiness`.

O relatorio publica `schema_version=user-test-readiness.v1`, `go_for_assisted_user_tests`, `ready_for_real_data`, `status`, `checks`, `counts`, `blockers`, `warnings` e garantias read-only em `safety`.

## Evidencia runtime local — 10/09/2026

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

Essas evidencias podem ser reutilizadas pelos gates reais quando seus contratos permitirem. Elas nao devem ser descartadas nem repetidas apenas para satisfazer checklists historicos.

`GO_ASSISTED` nao permite abertura ampla para usuarios com dados reais, seed global fora de janela autorizada, promocao manual de readiness nem tratar homologacao como declaracao fiscal/financeira final.

## Mapa canonico dos gates reais

### #226 — Proventos

O caminho portfolio-scoped usado na validacao assistida esta comprovado e idempotente. Permanece aberta a decisao operacional sobre cobertura real global e a evidencia exigida pelo gate de pre-producao. A prova assistida e evidencia parcial valida, nao substituto automatico do gate global.

### #216 — gate agregado

Benchmarks e cambio ja possuem evidencia consolidada. Proventos e o ultimo componente material a reconciliar. O fechamento depende da #226 no escopo operacional definido, nao da repeticao dos dominios ja certificados.

### #158 — rebuild pre-producao

Preparacao, backup, limpeza historica e grande parte do rebuild ja possuem evidencias. A execucao final deve operar sobre o delta necessario: importacao controlada da massa candidata, rebuild/reconciliacao final, validacao funcional e eventual contracao fisica explicitamente autorizada. Nao repetir etapas destrutivas ja certificadas apenas por estarem em checklist historico.

### #227 — GO/NO-GO

E a decisao formal de liberacao ampla. Deve consumir #303, #226, #216 e #158, alem de seguranca, resiliencia e homologacao. Somente uma decisao positiva pode autorizar a avaliacao/promocao de `ready_for_real_data=true`.

## Condicoes remanescentes

1. concluir rodada assistida sem blocker P0/P1 nas jornadas criticas e congelar SHA candidato;
2. fechar a estrategia operacional final de Proventos na #226, aproveitando a evidencia portfolio-scoped;
3. reconciliar e concluir #216;
4. executar o delta operacional final da #158 e reconciliar patrimonio, rentabilidade, Proventos, Tesouro, Renda Fixa e IRPF;
5. reconciliar eventos corporativos necessarios e definir tratamento dos eventos complexos `UNRECONCILED`;
6. repetir gates de seguranca/resiliencia aplicaveis sobre o mesmo SHA;
7. produzir GO/NO-GO formal na #227;
8. homologar no OCI o mesmo SHA certificado, sem desenvolvimento direto no servidor;
9. somente depois avaliar `ready_for_real_data=true` e a promocao estrutural para `main`.

A persistencia auditavel do estado de DARF pago permanece divida fiscal de produto. O gate final deve decidir explicitamente se ela bloqueia o escopo de abertura pretendido; a marcacao local atual nao deve ser tratada como persistencia fiscal definitiva.
