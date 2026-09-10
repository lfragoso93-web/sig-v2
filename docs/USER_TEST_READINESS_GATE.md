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

`GO_ASSISTED` nao permite:

- abertura ampla para usuarios com dados reais;
- seed real global fora de janela autorizada;
- promocao manual de readiness;
- tratar resultados de homologacao como declaracao fiscal ou financeira final.

## Proximos gates

Para avaliar `ready_for_real_data=true`, continuam pendentes:

1. duas execucoes reais controladas de Proventos (#226);
2. reconciliacao agregada do gate (#216);
3. importacao/rebuild operacional (#158);
4. decisao formal GO/NO-GO (#227);
5. persistencia auditavel de DARF paga;
6. reconciliacao minima de eventos corporativos e estrategia para eventos
   complexos.
