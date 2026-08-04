# Comparação controlada entre IRPF canônico e legado

## Objetivo

Este documento descreve o comparador read-only criado na Issue #56 para medir,
sem alterar o runtime de produção, as diferenças entre:

- `assess_annual_common_operations`, baseado em baixas canônicas; e
- `calc_ganhos_capital`, consumidor fiscal legado.

O comparador não define qual saída deve ser exposta ao usuário. Ele produz
evidência estruturada para a migração posterior.

## Escopo atual

A comparação considera somente operações comuns. Day Trade, IRRF, DARF mínima,
persistência de saldos e contratos públicos permanecem fora deste corte.

Para cada competência mensal são comparados:

- PnL realizado de Swing Trade/operações comuns;
- base tributável;
- imposto devido de Swing Trade/operações comuns;
- grupos fiscais presentes no caminho canônico.

## Classificações

- `match`: valores e presença mensal coincidem;
- `legacy_missing_month`: o canônico possui competência sem equivalente legado;
- `canonical_missing_month`: o legado possui competência sem equivalente canônico;
- `class_segregation`: a divergência envolve BDR, ETF, FII/Fiagro ou mais de um grupo;
- `stock_exemption`: o canônico aplicou isenção mensal de ações;
- `loss_carryforward`: o canônico consumiu prejuízo acumulado do mesmo grupo;
- `unknown`: divergência ainda não explicada pelas causas conhecidas.

As classificações podem coexistir na mesma competência.

## CLI individual

```bash
python -m app.cli.irpf_compare_legacy --portfolio-id 1 --year 2024
```

Contrato de saída: `irpf-canonical-legacy-comparison.v1`.

## CLI em lote

A descoberta operacional localiza automaticamente pares carteira/ano com ao
menos uma venda registrada e executa o comparador para cada alvo:

```bash
python -m app.cli.irpf_compare_legacy_batch
```

O intervalo pode ser restringido:

```bash
python -m app.cli.irpf_compare_legacy_batch --start-year 2022 --end-year 2026
```

Contrato de saída: `irpf-canonical-legacy-batch-comparison.v1`.

O relatório contém:

- alvos descobertos, contagem e intervalo das vendas;
- comparações executadas por carteira e ano;
- meses equivalentes e divergentes;
- contagem agregada por classificação de divergência;
- detalhe mensal com grupos fiscais canônicos.

Para automação, `--fail-on-divergence` retorna exit code `2` quando houver
qualquer mês divergente. Falhas operacionais retornam `1`; execução válida
retorna `0`.

As duas CLIs encerram a sessão com rollback explícito. Elas não alteram tabelas,
não persistem saldos fiscais e não substituem consumidores de produção.

## Matching quantitativo de Day Trade

O módulo puro `irpf_day_trade_matcher.py` caracteriza a fronteira correta para
Day Trade antes da migração do consumidor legado. A unidade fiscal intradiária
é o par data/ticker, mas somente a quantidade efetivamente comprada e vendida no
mesmo pregão é classificada como Day Trade.

Regras protegidas:

1. compras e vendas são casadas por FIFO dentro de data e ticker;
2. excedentes permanecem não casados para tratamento posterior como Swing Trade;
3. múltiplas operações intercaladas podem produzir vários matches;
4. taxas são rateadas proporcionalmente à quantidade casada;
5. o resultado bruto de cada match desconta taxas alocadas de compra e venda;
6. datas e tickers diferentes nunca são cruzados;
7. entradas inválidas são rejeitadas antes do matching.

Esse matcher ainda não é chamado por `calc_ganhos_capital` nem por endpoint de
produção. Ele constitui uma fundação isolada para o próximo adaptador fiscal.

## Escopo da página IRPF

A página IRPF usa a carteira selecionada no store global como parte das chaves
do React Query e das URLs de relatório, PDF e CSV. Ao trocar de carteira:

1. os anos disponíveis são consultados para a nova carteira;
2. o ano atual é preservado apenas se existir no novo conjunto;
3. caso contrário, o primeiro ano disponível é selecionado;
4. carteiras sem anos usam o ano-base padrão;
5. a aba retorna para `Resumo` e o sinal de recálculo é limpo.

A reconciliação é implementada pela função pura `reconcileIRPFYear` e protegida
por testes unitários e por um contrato estático de escopo frontend. Essa camada
não substitui a autorização do backend: todos os endpoints IRPF continuam
validando `portfolio_id` junto com o usuário autenticado.

## Invariantes arquiteturais

1. O comparador é read-only.
2. Nenhum endpoint ou schema público é alterado.
3. O motor canônico continua consumindo `CanonicalRealizedDisposal`.
4. O legado permanece inalterado durante a coleta de evidências.
5. Divergências entre classes não são ocultadas por consolidação anual.
6. A substituição do runtime só deve ocorrer após análise das divergências reais.
7. Os contratos JSON são versionados e adequados para evidência operacional.
8. A descoberta em lote considera vendas registradas, não presume que todo alvo
   produzirá uma baixa canônica válida.
9. O frontend nunca compartilha cache IRPF entre carteiras porque `portfolioId`
   permanece nas chaves de consulta.
10. A troca de carteira reconcilia ano e estado visual antes de seguir o fluxo.
11. O matcher quantitativo de Day Trade permanece puro e sem consumidores de
    produção até existir adaptador, comparação e gate de migração próprios.

## Próximos passos

1. validar Ruff e testes do matcher quantitativo;
2. criar adaptador de transações canônicas para `FiscalTradeOperation`;
3. consolidar matches Day Trade e excedentes Swing Trade por competência;
4. comparar o novo cálculo com o legado sem substituir o runtime;
5. executar a CLI em lote contra uma base com vendas reais.
