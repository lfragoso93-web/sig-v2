# Gate de readiness para testes assistidos

Atualizado em 10/09/2026.

## Objetivo

O gate `user-test-readiness.v1` consolida sinais operacionais para decidir se o
SGI v2 pode receber rodadas assistidas com usuarios convidados.

Ele nao substitui `/ready` e nao autoriza dados reais irrestritos. O ambiente
continua `ready_for_real_data=false` ate a decisao formal dos gates #226, #216,
#158 e #227.

## Como executar

No ambiente Docker:

```bash
docker-compose run --rm backend python -m app.cli.user_test_readiness
```

Como SuperAdmin:

```text
GET /api/v1/admin/bootstrap/user-test-readiness
```

## Contrato

O relatorio retorna:

- `schema_version`: sempre `user-test-readiness.v1`;
- `go_for_assisted_user_tests`: libera ou bloqueia rodada assistida;
- `ready_for_real_data`: espelha o gate real, sem promove-lo;
- `status`: `GO_ASSISTED` ou `NO_GO`;
- `checks`: lista de verificacoes com `code`, `status`, `detail` e `severity`;
- `counts`: contagens criticas de tabelas;
- `blockers`: falhas impeditivas;
- `warnings`: pendencias nao impeditivas para rodada assistida;
- `safety`: garantias de execucao read-only.

## Checks atuais

- `database_inventory`: exige inventario pre-prod sem findings bloqueantes e sem
  tabelas nao classificadas;
- `goals_runtime_schema`: exige a revision `20260910_goals_runtime`;
- `assisted_test_data_present`: exige usuarios, carteiras e transacoes;
- `market_history_present`: exige catalogo e historico de precos;
- `snapshot_history_present`: alerta se nao houver snapshots;
- `dividends_seed_present`: alerta se nao houver Proventos globais;
- `corporate_events_seed_present`: alerta se nao houver eventos corporativos;
- `real_data_gate_closed`: confirma que dados reais continuam fechados;
- `automatic_bootstrap_policy`: confirma bootstrap automatico desligado no
  ambiente de teste assistido.

## Evidencia runtime local

Execucao em 10/09/2026:

```text
schema_version=user-test-readiness.v1
status=GO_ASSISTED
go_for_assisted_user_tests=true
ready_for_real_data=false
blockers=[]
warnings=[]
```

Contagens observadas:

```text
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

`GO_ASSISTED` permite iniciar ou continuar testes acompanhados com usuarios
convidados, massa controlada e observacao tecnica.

A validacao assistida ja produziu evidencia real-controlada adicional sem abrir
o gate amplo:

- seed de Proventos escopado por carteira com prova de idempotencia;
- importacao CSV assistida seguida de rebuild e reconciliacao;
- reparos de historico de mercado e cobertura macro;
- validacao de Tesouro, Renda Fixa, IRPF e snapshots no runtime assistido;
- seed portfolio-scoped de eventos corporativos, ainda sem reconciliacao
  canonica dos eventos complexos.

Essas evidencias podem ser reutilizadas pelos gates reais quando seus contratos
permitirem. Elas nao devem ser descartadas nem repetidas apenas para satisfazer
checklists historicos.

`GO_ASSISTED` nao permite:

- abertura ampla para usuarios com dados reais;
- seed real global fora de janela autorizada;
- promocao manual de readiness;
- tratar resultados de homologacao como declaracao fiscal ou financeira final.

## Separacao dos gates reais

### #226 — Proventos

O caminho portfolio-scoped usado na validacao assistida esta comprovado e
idempotente. O que permanece aberto e a decisao operacional sobre cobertura
real global e a evidencia exigida para o gate de pre-producao. A #226 nao deve
voltar a exigir trabalho ja comprovado no escopo assistido; deve registrar a
diferenca entre a prova portfolio-scoped e o gate global.

### #216 — gate agregado

Benchmarks e cambio ja possuem evidencia consolidada. Proventos e o ultimo
componente material a reconciliar no gate agregado antes da janela operacional
final.

### #158 — rebuild pre-producao

A #158 deve preservar as etapas destrutivas/estruturais ja certificadas e
executar somente o delta operacional ainda necessario: importacao controlada,
rebuild/reconciliacao final, validacao funcional e, quando autorizada, eventual
contracao fisica protegida. Nao repetir limpeza ou rebuild amplo apenas por
historico de checklist.

### #227 — GO/NO-GO

A #227 e a unica decisao formal de liberacao ampla. Deve consumir as evidencias
da #303, #226, #216 e #158, mais seguranca/resiliencia/homologacao, antes de
qualquer alteracao de `ready_for_real_data`.

## Proximos gates

Para avaliar `ready_for_real_data=true`, continuam pendentes:

1. fechar a estrategia operacional final de Proventos na #226, considerando a
   evidencia portfolio-scoped ja aprovada;
2. reconciliar e concluir o gate agregado #216;
3. executar o delta operacional final da #158 com importacao/rebuild e
   reconciliacao controlados;
4. reconciliar eventos corporativos necessarios para os ativos da carteira e
   definir tratamento dos eventos complexos ainda `UNRECONCILED`;
5. concluir a rodada assistida sem blocker P0/P1 nas jornadas criticas;
6. produzir decisao formal GO/NO-GO na #227;
7. somente depois avaliar `ready_for_real_data=true`.

A persistencia auditavel do estado de DARF pago permanece divida fiscal de
produto; o gate deve avaliar se ela bloqueia o escopo de abertura pretendido,
sem confundir a marcacao local atual com persistencia fiscal definitiva.
