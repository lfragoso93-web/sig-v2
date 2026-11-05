# Ferramentas e Simuladores Financeiros

O menu de **Ferramentas** do SGI disponibiliza simuladores independentes para planejar aportes futuros e comparar alternativas de investimento em renda fixa.

---

## 1. Calculadora de Rendimentos e Juros Compostos

Acesse pelo menu lateral em **Ferramentas ➔ Calculadora** (`/carteira/ferramentas/rendimentos`).

A Calculadora permite simular o crescimento de um patrimônio com aportes recorrentes e taxas de juros compostos:
- **Aporte Inicial**: Valor em dinheiro disponível para começar imediatamente.
- **Aporte Mensal**: Quantia a ser economizada e reinvestida a cada mês.
- **Taxa Efetiva Anual**: Taxa de retorno anual estimada (ex.: 10% ou 12% ao ano).
- **Prazo**: Período da simulação em meses (de 1 a 600 meses).

### Premissas da simulação:
O simulador calcula o valor futuro com premissas fixas:
- A taxa mensal equivalente é calculada matematicamente por $(1 + \text{taxa anual})^{1/12} - 1$.
- O aporte inicial entra no mês zero; a cada mês subsequente, o saldo acumulado rende os juros mensais e o novo aporte é incorporado no fechamento do período.
- Recorrência utilizada: $\text{Saldo}_m = \text{Saldo}_{m-1} \times (1 + \text{taxa mensal}) + \text{Aporte Mensal}$.
- O total aportado é a soma do aporte inicial mais a soma dos aportes mensais; o ganho de juros projetado é a diferença entre o saldo final e o total aportado.
- O simulador nao modela resgate antecipado, inflação nem volatilidade diária de mercado; trata-se de projeção matemática educacional.

---

## 2. Comparador de Títulos de Renda Fixa

Acesse pelo menu lateral em **Ferramentas ➔ Simulador RF** (`/carteira/ferramentas/renda-fixa`).

O Comparador analisa lado a lado dois títulos de renda fixa com tratamentos fiscais diferentes (por exemplo: um CDB que paga 115% do CDI contra uma LCI que paga 95% do CDI):

### Enquadramento Fiscal Automático:
- **Títulos Tributáveis (Tabela Regressiva de IR)**: CDB, RDB, LC, Letra Financeira e Debêntures comuns.
  * Até 180 dias: 22,5% de alíquota de Imposto de Renda
  * De 181 a 360 dias: 20,0% de alíquota
  * De 361 a 720 dias: 17,5% de alíquota
  * Acima de 720 dias: 15,0% de alíquota
- **Títulos Isentos de IR (Pessoa Física)**: LCI, LCA, LIG, CRI, CRA e Debêntures Incentivadas (Lei 11.033/2004 e Lei 12.431/2011).

### Indicador de Taxa Equivalente Líquida:
O simulador calcula automaticamente qual taxa bruta o título tributável precisaria pagar para empatar exatamente com o rendimento líquido do título isento no mesmo prazo em dias corridos, facilitando a escolha da alternativa mais rentável.
