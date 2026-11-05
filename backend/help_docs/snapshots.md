# Snapshots Patrimoniais e Fechamento Diário

Os **Snapshots Patrimoniais** constituem os marcos oficiais de fechamento diário da sua carteira no SGI.

---

## 1. O Papel do Snapshot Diário

Diferente de sistemas que calculam o patrimônio apenas dinamicamente no momento da visualização, o SGI grava um snapshot histórico diário consolidado às **21h (horário de Brasília)**, todos os dias do ano, incluindo fins de semana e feriados.

Cada registro de snapshot preserva permanentemente:
- **Valor de Mercado**: Patrimônio total consolidado calculado com as cotações oficiais do dia.
- **Custo em Aberto**: Valor total de aquisição investido nas posições ativas.
- **Ganhos Realizados e Não Realizados**: Lucros ou prejuízos acumulados e abertos na data.
- **Fluxos Externos do Dia**: Aportes e retiradas realizados na carteira no período.
- **Proventos do Dia e Proventos Acumulados**: Dividendos e rendimentos com data de pagamento na data.
- **Retorno Diário**: Rentabilidade percentual líquida apurada nas 24 horas.
- **Retorno Acumulado (`accumulated_return_pct`)**: Taxa geométrica acumulada da carteira desde o início.

---

## 2. Princípio de Dados Auditáveis

A rotina de consolidação às 21h utiliza exclusivamente dados consolidados e persistidos no banco de dados:
- Nos fins de semana e feriados em que a bolsa não opera, o snapshot utiliza os últimos preços oficiais disponíveis para ativos de bolsa e as cotações contínuas de fim de semana para criptoativos.
- O snapshot **não cria movimentações financeiras artificiais** e não substitui o livro-razão de transações.

---

## 3. Retorno diário e tratamento de fluxos

O retorno percentual diário expurga os fluxos de caixa externos (novos aportes ou saques) para não distorcer o desempenho real:

$$r_{\text{dia}} = \frac{\text{Valor Final} - \text{Valor Inicial} - \text{Fluxo Líquido} + \text{Proventos}}{\text{Valor Inicial}}$$

---

## 4. Retorno acumulado

A taxa de retorno acumulado é composta progressivamente multiplicando-se os fatores de retorno de cada dia de vida da carteira:

$$(1 + r_1) \times (1 + r_2) \times \dots \times (1 + r_n) - 1$$

Essa rentabilidade consolidada é gravada no snapshot mais recente no campo `accumulated_return_pct`, alimentando com precisão matemática os gráficos de evolução patrimonial e a matriz anual de rentabilidade do investidor.
