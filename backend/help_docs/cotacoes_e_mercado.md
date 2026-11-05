# Cotações e Dados de Mercado

O SGI mantém um pipeline contínuo de sincronização de cotações para manter os valores patrimoniais da sua carteira atualizados e confiáveis.

---

## 1. Grade de Horários de Atualização

Todas as rotinas seguem o horário oficial de Brasília (BRT):

| Período | Horário | Escopo de Ativos |
| :--- | :--- | :--- |
| **Pregão Oficial (Dias Úteis)** | De hora em hora, entre 09h e 18h | Ações B3, FIIs, BDRs, ETFs, Índices e Renda Variável Internacional |
| **Mercado Cripto (Ininterrupto)** | De hora em hora, 24 horas por dia, 7 dias por semana | Criptomoedas e ativos digitais globais (Bitcoin, Ethereum, etc.) |
| **Fechamento Diário Oficial** | Todos os dias, às 21h (inclusive finais de semana e feriados) | Snapshot patrimonial oficial consolidado com os preços finais de fechamento |

---

## 2. Fontes de Dados e Integração

O SGI integra informações de fontes oficiais e provedores de mercado:
- **B3 (Bolsa de Valores do Brasil)**: Cotações oficiais de negociação, preços de fechamento diários e histórico de ativos listados.
- **Banco Central do Brasil (BCB)**: Séries econômicas oficiais, incluindo taxas CDI diárias, meta Selic e taxas de câmbio (PTAX Dólar) para ativos internacionais.
- **Tesouro Nacional**: Séries históricas e taxas de compra/venda de títulos públicos do Tesouro Direto.

---

## 3. Princípio de Não Invenção de Preços

Em respeito à governança dos seus investimentos:
- Se um determinado ativo ilíquido não tiver negócios registrados no pregão ou se o provedor não disponibilizar cotação oficial na data, o SGI **não inventa valores nem cria estimativas artificiais**.
- O sistema mantém o último preço oficial persistido e identifica a posição com o selo de **cobertura parcial**.
- Essa abordagem garante que os relatórios contábeis e fiscais do investidor reflitam apenas fatos econômicos auditáveis.
