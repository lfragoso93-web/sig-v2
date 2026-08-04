# Comparação controlada entre IRPF canônico e legado

## Objetivo

Este documento descreve os comparadores read-only criados na Issue #56 para
medir, sem alterar o runtime de produção, as diferenças entre o caminho canônico
e `calc_ganhos_capital`.

O comparador não define qual saída deve ser exposta ao usuário. Ele produz
evidência estruturada para a migração posterior.

## Escopo atual

A comparação integrada considera Swing Trade e Day Trade por competência. IRRF,
DARF mínima, persistência de saldos e contratos públicos permanecem fora deste
corte.

Para cada competência mensal são comparados:

- resultado realizado Swing;
- base tributável Swing;
- imposto Swing;
- resultado Day Trade;
- base tributável Day Trade;
- imposto Day Trade.

## Comparador integrado mensal

O módulo `irpf_integrated_legacy_comparison.py` alinha a apuração anual integrada
com a saída mensal de `calc_ganhos_capital` e produz classificações que podem
coexistir:

- `match`;
- `legacy_missing_month`;
- `canonical_missing_month`;
- `swing_result`;
- `swing_taxable_base`;
- `swing_tax_due`;
- `day_trade_result`;
- `day_trade_taxable_base`;
- `day_trade_tax_due`;
- `loss_carryforward`.

O serviço `irpf_integrated_comparison_service.py` executa cada caminho uma única
vez e devolve a visão comparativa anual. O fluxo permanece read-only, não
persiste resultados e não substitui consumidores de produção.

## CLI individual de operações comuns

```bash
python -m app.cli.irpf_compare_legacy --portfolio-id 1 --year 2024
```

Contrato de saída: `irpf-canonical-legacy-comparison.v1`.

## CLI em lote de operações comuns

```bash
python -m app.cli.irpf_compare_legacy_batch
```

O intervalo pode ser restringido:

```bash
python -m app.cli.irpf_compare_legacy_batch --start-year 2022 --end-year 2026
```

Contrato de saída: `irpf-canonical-legacy-batch-comparison.v1`.

Para automação, `--fail-on-divergence` retorna exit code `2` quando houver
qualquer mês divergente. Falhas operacionais retornam `1`; execução válida
retorna `0`.

## Matching quantitativo de Day Trade

O módulo puro `irpf_day_trade_matcher.py` caracteriza a fronteira correta para
Day Trade. A unidade fiscal intradiária é o par data/ticker, mas somente a
quantidade efetivamente comprada e vendida no mesmo pregão é classificada como
Day Trade.

Regras protegidas:

1. compras e vendas são casadas por FIFO dentro de data e ticker;
2. excedentes permanecem não casados para tratamento posterior como Swing Trade;
3. múltiplas operações intercaladas podem produzir vários matches;
4. taxas são rateadas proporcionalmente à quantidade casada;
5. o resultado bruto desconta taxas alocadas de compra e venda;
6. datas e tickers diferentes nunca são cruzados;
7. entradas inválidas são rejeitadas antes do matching.

## Adaptador e projeção mensal

`irpf_day_trade_transaction_adapter.py` converte transações persistidas para
`FiscalTradeOperation` e aplica ordenação determinística por data e id.

`irpf_day_trade_monthly_projection.py` consolida por competência:

- quantidade casada como Day Trade;
- resultado intradiário após taxas;
- quantidade comprada não casada;
- quantidade vendida não casada;
- matches detalhados.

## Apuração mensal de Day Trade

`irpf_day_trade_monthly_assessment.py` aplica:

1. alíquota fixa de 20%;
2. arredondamento monetário em centavos;
3. prejuízos transportados somente entre competências Day Trade;
4. compensação sem cruzamento com Swing ou classes comuns;
5. saldo inicial, prejuízo usado, saldo final, base e imposto explícitos.

O módulo continua read-only e não aplica IRRF nem DARF mínima.

## Comparador específico de Day Trade

`irpf_day_trade_legacy_comparison.py` compara quantidade e resultado mensal com a
visão legada. Classificações:

- `match`;
- `legacy_missing_month`;
- `canonical_missing_month`;
- `day_trade_quantity`;
- `day_trade_result`.

A CLI dedicada é:

```bash
python -m app.cli.irpf_compare_day_trade --portfolio-id 1 --year 2024
```

Contrato: `irpf-day-trade-canonical-legacy-comparison.v1`.

## Projeção de excedentes Swing

`irpf_swing_remainder_projection.py` recebe baixas canônicas e matches Day
Trade. Ele não recalcula posição ou custo médio. O módulo:

1. agrega a quantidade intradiária por `sell_transaction_id`;
2. remove baixas integralmente consumidas pelo Day Trade;
3. preserva baixas sem parcela intradiária;
4. reduz proporcionalmente baixas parciais;
5. rateia proventos, custo, taxas, PnL e moeda original;
6. preserva metadados financeiros.

## Apuração anual integrada read-only

`irpf_annual_integrated_assessment_service.py`:

1. carrega transações uma única vez;
2. projeta Day Trade quantitativo;
3. aplica política mensal Day Trade de 20% com compensação segregada;
4. carrega baixas canônicas uma única vez;
5. remove a parcela intradiária das baixas Swing;
6. reaproveita política, isenção e compensação comuns existentes;
7. consolida resultado, base, imposto e prejuízo Day Trade;
8. consolida PnL, base e imposto Swing;
9. expõe imposto total combinado.

O serviço não recalcula custo médio, não persiste resultados e não altera
`calc_ganhos_capital`.

## Escopo da página IRPF

A página IRPF usa a carteira selecionada nas chaves do React Query e nas URLs de
relatório, PDF e CSV. Ao trocar de carteira, o ano é reconciliado com os anos
disponíveis e o estado visual retorna ao resumo.

## Invariantes arquiteturais

1. Todos os comparadores são read-only.
2. Nenhum endpoint ou schema público é alterado neste estágio.
3. O motor canônico continua consumindo `CanonicalRealizedDisposal`.
4. O legado permanece inalterado durante a coleta de evidências.
5. Divergências Swing e Day Trade não são ocultadas por consolidação anual.
6. A substituição do runtime depende de evidência operacional real.
7. Prejuízos Day Trade nunca compensam operações comuns.
8. A projeção Swing não reimplementa custo médio nem posição.
9. Cada caminho integrado e legado é executado uma única vez por comparação.
10. IRRF e DARF mínima permanecem gates separados.

## Próximos passos

1. validar Ruff e testes do comparador integrado;
2. expor uma CLI JSON versionada para a comparação integrada;
3. executar a comparação em dados reais e inventariar divergências;
4. ampliar classificações com custos, FX e arredondamento;
5. incorporar IRRF e DARF mínima em blocos próprios;
6. definir o gate objetivo de substituição do runtime legado.
