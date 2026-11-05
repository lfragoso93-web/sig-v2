# Radar Fiscal e Imposto de Renda (IRPF)

A página de **IRPF** atua como um radar fiscal contínuo para apoiar o investidor na apuração mensal de resultados, controle de limites de isenção, compensação de prejuízos e memória de cálculo para apuração de DARF.

---

## 1. Regras Oficiais de Tributação no Mercado de Capitais

A legislação tributária brasileira estabelece tratamentos específicos por classe de ativo e tipo de operação:

| Classe de Ativo | Modalidade | Isenção Mensal | Alíquota sobre Lucro |
| :--- | :--- | :--- | :--- |
| **Ações Brasileiras** | Swing Trade (posições mantidas por mais de um dia) | **R$ 20.000,00** no total de vendas no mês | 15% sobre o ganho líquido (se vendas > R$ 20.000) |
| **Ações Brasileiras** | Day Trade (compra e venda no mesmo dia) | **Não há isenção** | 20% sobre o ganho líquido |
| **Fundos Imobiliários (FIIs)** | Qualquer modalidade | **Não há isenção** | 20% sobre o ganho líquido de capital |
| **ETFs de Ações e BDRs** | Swing Trade | **Não há isenção** | 15% sobre o ganho líquido |
| **Criptomoedas** | Vendas mensais | **R$ 35.000,00** no mês (conjunto de criptoativos) | 15% sobre o ganho líquido (se vendas > R$ 35.000) |

---

## 2. A Isenção de R$ 20.000 para Ações (Swing Trade)

O limite de isenção de R$ 20.000,00 é mensal e aplica-se à soma de todas as vendas de ações no mercado à vista brasileiro:
- **Vendas totais $\le$ R$ 20.000,00 no mês**: Qualquer lucro apurado é isento de Imposto de Renda. Não é gerada obrigação de DARF. O ganho deve ser lançado na ficha de "Rendimentos Isentos e Não Tributáveis" na declaração anual.
- **Vendas totais $>$ R$ 20.000,00 no mês**: Todo o lucro líquido obtido nas operações com ações naquele mês é tributável à alíquota de 15%.

> **Importante**: Operações com FIIs, ETFs e BDRs **não** contam para o limite de R$ 20.000 e não desfrutam de isenção; todo ganho nessas categorias é tributável independentemente do valor transacionado.

---

## 3. Compensação de Prejuízos Acumulados

Se você realizou vendas com prejuízo:
- O SGI mantém o controle contínuo do **saldo de prejuízos acumulados** a compensar.
- Prejuízos de Swing Trade em ações abatem lucros futuros de Swing Trade.
- Prejuízos de Day Trade abatem exclusivamente lucros de Day Trade.
- Prejuízos em FIIs abatem exclusivamente lucros futuros em FIIs.
- Ao obter lucro em um mês subsequente, o sistema abate primeiro o prejuízo histórico antes de aplicar a alíquota de imposto, reduzindo legalmente o valor a pagar.

---

## 4. Apuração e Memória de Cálculo de DARF

Quando for apurado imposto devido em determinado mês:
- O SGI calcula o valor líquido do imposto devido, deduzindo eventuais retenções de "imposto dedo-duro" (IRRF retido pela corretora nas notas), permitindo a exportação do relatório de memória de cálculo e a sinalização de meses quitados.
- **Importante**: O SGI não emite a guia DARF bancária com código de barras nem possui integração com o Sicalc Web. A emissão do documento de arrecadação e o pagamento devem ser realizados pelo investidor diretamente no Sicalcweb da Receita Federal ou pelo internet banking utilizando os dados fornecidos pelo SGI.
- **Código de Receita**:
  * Operações de Bolsa (Pessoa Física): **6015**
- **Vencimento**: O imposto deve ser recolhido até o último dia útil do mês subsequente ao das operações.
- **Valor mínimo**: Caso o imposto devido no mês seja inferior a R$ 10,00, a legislação veda o pagamento avulso; o valor é acumulado para recolhimento futuro quando ultrapassar R$ 10,00.

---

## 5. Apoio à Declaração de Ajuste Anual

No fechamento do ano-calendário, o SGI consolida as informações necessárias para preencher o programa da Receita Federal:
1. **Bens e Direitos**: Custo total de aquisição dos ativos mantidos em custódia em 31 de dezembro de cada ano (lembrando que a Receita exige o custo de aquisição, e não o valor de cotação de mercado).
2. **Rendimentos Isentos**: Dividendos recebidos e lucros auferidos dentro da faixa de isenção de R$ 20.000.
3. **Rendimentos Sujeitos à Tributação Exclusiva**: Juros sobre Capital Próprio (JCP) líquidos recebidos.
4. **Renda Variável**: Resumo mensal de ganhos/perdas e imposto pago para preenchimento da aba de Renda Variável.

> **Aviso Legal**: O módulo de IRPF do SGI é uma ferramenta de gestão e apoio à conferência. Sempre valide seus cálculos com os informes de rendimentos oficiais disponibilizados pelas corretoras, bancos custodiantes e escrituradores.
