# Patrimônio e Custódia Multiclasse

A página de **Patrimônio** apresenta a radiografia completa de todos os ativos sob sua custódia, detalhando quantidade em carteira, custo de aquisição, cotação atual e valor de mercado consolidado.

---

## 1. Como a Custódia e o Preço Médio são Calculados

No SGI, a custódia não é digitada manualmente; ela é uma projeção matemática rigorosa do seu histórico de transações:
- **Quantidade em Aberto**: Soma das compras deduzida das vendas e ajustada por eventos corporativos (splits, grupamentos e bonificações).
- **Preço Médio de Aquisição (PM)**: Calculado pela média ponderada pelo custo de cada compra, acrescido das taxas e custos operacionais informados:
  $$\text{Preço Médio} = \frac{\sum (\text{Quantidade Comprada} \times \text{Preço Unitário} + \text{Custos})}{\text{Quantidade Total Comprada}}$$
- **Vendas não alteram o preço médio**: A realização de lucros ou prejuízos reduz o saldo de cotas, mas preserva o custo unitário médio das unidades remanescentes.

---

## 2. As 8 Classes de Ativos Suportadas

O SGI foi arquitetado para investidores com carteiras sofisticadas e diversificadas:

1. **Ações Brasileiras (B3)**: Ações ordinárias (ON), preferenciais (PN) e units negociadas no mercado à vista brasileiro.
2. **Fundos de Investimento Imobiliário (FIIs)**: Fundos de tijolo, papel, Fiagro e fundos de infraestrutura, com acompanhamento de cotas e rendimentos mensais.
3. **Tesouro Direto**: Títulos públicos federais indexados à Selic (Tesouro Selic), à inflação (Tesouro IPCA+ com ou sem juros semestrais) e Prefixados.
4. **Renda Fixa Privada**: Títulos bancários e de crédito corporativo, como CDBs, LCIs, LCAs, CRIs, CRAs e Debêntures (comuns e incentivadas).
5. **ETFs (Exchange Traded Funds)**: Fundos de índices negociados em bolsa, tanto locais (ex.: BOVA11, SMAL11) quanto globais listados no Brasil (ex.: IVVB11).
6. **Criptomoedas e Ativos Digitais**: Principais moedas descentralizadas (Bitcoin, Ethereum, Solana, etc.) com negociação contínua 24/7.
7. **BDRs (Brazilian Depositary Receipts)**: Certificados representativos de empresas multinacionais negociados diretamente na B3 em reais (ex.: AAPL34, MSFT34).
8. **Ativos Internacionais em Dólar (USD)**: Ações e REITs negociados em bolsas internacionais (NYSE, Nasdaq), com suporte a conversão cambial e custódia em moeda estrangeira.

---

## 3. Entendendo os Indicadores da Tabela de Posições

Ao navegar pela lista de ativos na página de Patrimônio:
- **Ativo / Nome**: Código de negociação (ticker) e razão social do ativo.
- **Quantidade**: Total de papéis ou frações atualmente em sua posse.
- **Preço Médio**: Custo médio ponderado por cota pago na aquisição.
- **Cotação Atual**: Último preço de fechamento ou preço intradiário registrado para o ativo.
- **Valor Investido (Custo Total)**: $\text{Quantidade} \times \text{Preço Médio}$.
- **Valor Atual (Mercado)**: $\text{Quantidade} \times \text{Cotação Atual}$.
- **Ganho / Perda Não Realizado**: Diferença monetária ($\text{Valor Atual} - \text{Valor Investido}$) e percentual entre o valor presente e o custo histórico.
- **% na Carteira**: Participação percentual do ativo em relação ao patrimônio total consolidado.

---

## 4. Posições Encerradas e Histórico

Quando você aliena a totalidade de um ativo (quantidade atinge zero):
- A posição é movida para a seção de **Posições Encerradas**.
- O ganho ou perda de capital realizado é registrado definitivamente para fins de apuração fiscal e histórico de desempenho da carteira.
- Se você voltar a comprar o papel no futuro, uma nova contagem de preço médio será iniciada a partir do novo preço de aquisição.

---

## 5. Transparência na Cobertura de Preços

O SGI preza pela transparência matemática absoluta:
- Se um ativo ilíquido ou de balcão não tiver cotação pública atualizada na data de consulta, o sistema indica a cobertura como **parcial** e utiliza o último preço persistido confiável.
- O sistema **nunca inventa preços** para fechar gráficos artificiais.
