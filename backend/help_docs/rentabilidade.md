# Rentabilidade da Carteira

A página de **Rentabilidade** apresenta a evolução do retorno dos seus investimentos calculada pela metodologia padrão institucional do mercado global.

---

## 1. Separação Fundamental: Resultado Financeiro vs Rentabilidade Percentual

O SGI separa com clareza dois conceitos que frequentemente geram confusão no investidor:

| Conceito | Natureza | Exemplo | O que mede |
| :--- | :--- | :--- | :--- |
| **Resultado Financeiro** | Valor monetário em reais | + R$ 14.850,00 | O lucro líquido absoluto obtido pela carteira (ganhos realizados, ganhos não realizados e proventos). |
| **Rentabilidade (TWR)** | Taxa percentual composta | + 18,45% | A eficiência real da sua gestão no tempo, independentemente de você ter feito aportes grandes ou pequenos. |

---

## 2. Metodologia TWR (Time-Weighted Return)

O **TWR (Retorno Ponderado pelo Tempo)** é o padrão internacional exigido por órgãos reguladores (como o CFA Institute / GIPS) para mensurar desempenho de carteiras e fundos.

### Por que o TWR é indispensável?
Se você possui R$ 10.000 aplicados e a carteira valoriza 10% (ganho de R$ 1.000), seu saldo vai para R$ 11.000. Se no dia seguinte você aporta mais R$ 100.000, seu patrimônio salta para R$ 111.000.  
Se calculássemos a rentabilidade pela simples divisão do saldo final pelo inicial, o retorno pareceria de mais de 1.000%, o que seria completamente falso!  
O TWR quebra a linha do tempo em subperíodos delimitados por cada movimentação de caixa (aportes ou resgates), calculando a taxa de retorno puramente dos ativos.

### Fórmula do retorno diário:
Para cada dia de negociação:
$$r_t = \frac{\text{Valor Final} - \text{Valor Inicial} - \text{Fluxo Líquido} + \text{Proventos do Dia}}{\text{Valor Inicial}}$$

---

## 3. Retorno acumulado

O retorno acumulado no tempo é calculado pela composição geométrica (multiplicação de fatores) de cada retorno diário:

$$(1 + r_1) \times (1 + r_2) \times \dots \times (1 + r_n) - 1$$

Esse percentual acumulado compõe a série histórica e é registrado em cada snapshot diário da carteira através do indicador `accumulated_return_pct`.

---

## 4. Matriz Mensal e Cálculo do "No Ano"

Na tabela da Matriz de Rentabilidade:
- **Linhas e Colunas**: Cada célula representa o retorno efetivo apurado naquele mês do ano (de Janeiro a Dezembro).
- **Coluna "No Ano" (Year to Date - YTD)**: Representa o retorno composto de todos os meses decorridos no ano civil.
- **Atenção**: As taxas mensais **não são somadas**. Se a carteira rendeu +2% em janeiro e +3% em fevereiro, o retorno no ano é $(1 + 0{,}02) \times (1 + 0{,}03) - 1 = +5{,}06\%$ (efeito dos juros compostos).

---

## 5. Comparativo com Benchmarks Oficiais

O SGI compara o desempenho da sua carteira contra os dois principais referenciais da economia brasileira:
- **CDI (Certificado de Depósito Interbancário)**: O benchmark de referência para a renda fixa e custo de oportunidade do capital.
- **IBOVESPA (IBOV)**: O principal índice de ações da bolsa de valores brasileira.

O gráfico de rentabilidade relativa permite avaliar se sua estratégia de alocação está gerando alfa (retorno excedente acima do mercado) no médio e longo prazo.

---

## 6. Cards de Desempenho Rápido

No topo da tela de Rentabilidade, você encontra quatro períodos consolidados:
1. **Hoje**: Retorno apurado no dia em curso.
2. **No Mês**: Retorno acumulado no mês corrente.
3. **Em 12 Meses**: Retorno composto móvel dos últimos doze meses.
4. **Desde o Início**: Retorno histórico completo acumulado desde o primeiro dia de vida da carteira.
