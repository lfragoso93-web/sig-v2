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

As CLIs encerram a sessão com rollback explícito. Elas não alteram tabelas,
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

## Adaptador e projeção mensal

O módulo `irpf_day_trade_transaction_adapter.py` converte transações persistidas
para `FiscalTradeOperation` e aplica ordenação determinística por data e id. A
conversão prefere `price_brl` persistido quando disponível e usa `price` apenas
como fallback de compatibilidade.

O módulo `irpf_day_trade_monthly_projection.py` consolida por competência:

- quantidade efetivamente casada como Day Trade;
- resultado bruto intradiário após taxas alocadas;
- quantidade comprada não casada;
- quantidade vendida não casada;
- matches detalhados da competência.

A projeção identifica a fronteira quantitativa entre Day Trade e excedentes que
seguirão para Swing Trade, mas ainda não calcula custo médio, PnL ou imposto dos
excedentes Swing. Essa responsabilidade continuará no projetor canônico de
baixas e na camada de política fiscal.

Nenhum desses módulos é chamado por `calc_ganhos_capital` ou por endpoint de
produção.

## Apuração mensal de Day Trade

O módulo `irpf_day_trade_monthly_assessment.py` consome a projeção quantitativa e
aplica a política fiscal exclusiva de Day Trade:

1. alíquota fixa de 20%;
2. arredondamento monetário determinístico em centavos;
3. prejuízos transportados cronologicamente apenas entre competências Day Trade;
4. compensação sem cruzamento com Swing Trade, ações, ETF, BDR, FII ou Fiagro;
5. exposição explícita de saldo inicial, prejuízo usado, saldo final, base e imposto.

O módulo continua read-only e não aplica IRRF nem DARF mínima.

## Comparador específico de Day Trade

O módulo `irpf_day_trade_legacy_comparison.py` compara, competência a competência,
a projeção quantitativa com uma visão mensal do comportamento legado. O contrato
read-only expõe quantidade casada, resultado intradiário e deltas explícitos.

Classificações disponíveis:

- `match`;
- `legacy_missing_month`;
- `canonical_missing_month`;
- `day_trade_quantity`;
- `day_trade_result`.

As classificações podem coexistir na mesma competência.

O serviço `irpf_day_trade_comparison_service.py` carrega as transações da
carteira e ano, gera a projeção quantitativa, executa `calc_ganhos_capital`
apenas como referência legada e extrai das vendas marcadas como Day Trade a
quantidade mensal comparável. O serviço não persiste resultados.

A CLI dedicada pode ser executada dentro do container backend:

```bash
python -m app.cli.irpf_compare_day_trade --portfolio-id 1 --year 2024
```

Contrato de saída:
`irpf-day-trade-canonical-legacy-comparison.v1`.

Com `--fail-on-divergence`, a CLI retorna exit code `2` quando houver qualquer
competência divergente. Erros operacionais retornam `1` e execução válida
retorna `0`. A sessão é encerrada com rollback explícito.

## Projeção de excedentes Swing

O módulo `irpf_swing_remainder_projection.py` recebe baixas financeiras
canônicas e os matches Day Trade já identificados. Ele não recalcula posição,
custo médio ou PnL. Em vez disso:

1. agrega por `sell_transaction_id` a quantidade intradiária casada;
2. remove baixas consumidas integralmente pelo Day Trade;
3. preserva baixas sem parcela intradiária;
4. reduz proporcionalmente baixas parcialmente intradiárias;
5. rateia proventos, custo, taxas, PnL e valor na moeda original;
6. preserva ticker, classe, data, preço unitário e eventos corporativos aplicados.

Baixas sem `transaction_id` são preservadas porque não existe vínculo seguro com
o matcher. Essa visão continua read-only e ainda não substitui o pipeline anual
de operações comuns.

## Apuração anual integrada read-only

O serviço `irpf_annual_integrated_assessment_service.py` compõe os contratos
anteriores em um único fluxo anual paralelo:

1. carrega transações da carteira e ano uma única vez;
2. adapta e projeta o Day Trade quantitativo;
3. aplica a política mensal Day Trade de 20% com compensação segregada;
4. carrega baixas canônicas realizadas uma única vez;
5. remove dessas baixas a parcela intradiária já casada;
6. reaproveita adaptador fiscal, agrupamento mensal, política, isenção e
   compensação de prejuízos já existentes para o excedente Swing;
7. consolida resultado, base, imposto e prejuízo final de Day Trade;
8. consolida PnL, base e imposto Swing;
9. expõe o imposto total combinado da visão paralela.

O serviço não recalcula custo médio, não persiste resultados e não altera o
runtime de `calc_ganhos_capital`. IRRF e DARF mínima permanecem fora deste corte.

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
11. O matcher, o adaptador, a projeção mensal, o comparador e a CLI de Day Trade
    permanecem isolados de consumidores de produção até existir gate próprio.
12. Excedentes não casados não recebem custo Swing dentro do matcher; essa
    responsabilidade permanece no projetor canônico de baixas.
13. A visão legada de Day Trade é derivada somente para comparação e não se torna
    fonte de verdade do novo motor.
14. A projeção de excedentes Swing reduz baixas canônicas por proporção e não
    reimplementa custo médio nem posição.
15. A apuração anual integrada reutiliza os módulos canônicos de política,
    isenção e prejuízos e não cria um segundo motor fiscal Swing.
16. Prejuízos Day Trade permanecem segregados e nunca compensam operações comuns.

## Próximos passos

1. validar Ruff e testes da política mensal Day Trade e da apuração integrada;
2. comparar a apuração anual integrada com o legado por competência;
3. ampliar a classificação de divergências com custos, FX e arredondamento;
4. incorporar IRRF e DARF mínima em blocos próprios;
5. definir o gate objetivo de substituição do runtime legado.
