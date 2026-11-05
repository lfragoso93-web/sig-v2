# Transações e Registro de Operações

As transações registradas no SGI formam o livro-razão (ledger) canônico da carteira. A partir delas, a plataforma projeta automaticamente sua custódia atual, calcula o preço médio de aquisição e apura ganhos ou perdas fiscais.

---

## 1. Tipos de Operação Suportados

O SGI contempla todas as modalidades operacionais do mercado de capitais:

| Tipo | Descrição | Impacto na Carteira |
| :--- | :--- | :--- |
| **Compra** | Aquisição de novos ativos (ações, cotas, títulos, contratos). | Aumenta a quantidade em custódia e recalcula o preço médio ponderado. |
| **Venda** | Alienação total ou parcial de ativos em carteira. | Reduz a quantidade em custódia, apura o resultado fiscal (lucro/prejuízo) e mantém o preço médio inalterado. |
| **Desdobramento (Split)** | Aumento da quantidade de cotas/ações sem alteração no valor investido. | Aumenta o número de papéis e reduz proporcionalmente o preço médio. |
| **Grupamento (Reverse Split)** | Redução da quantidade de cotas/ações sem alteração no valor investido. | Reduz o número de papéis e eleva proporcionalmente o preço médio. |
| **Bonificação em Ativos** | Distribuição gratuita de novas ações aos acionistas. | Aumenta a quantidade e incorpora o custo de atribuição informado pela empresa ao custo total. |
| **Rendimento / Provento** | Pagamento monetário de dividendos, JCP ou aluguéis de FIIs. | Registra a receita em dinheiro sem alterar a quantidade de cotas em custódia. |

---

## 2. Como Lançar uma Operação

Você pode registrar uma transação de duas maneiras:
1. Pelo atalho rápido de teclado: pressione **`Alt + N`** em qualquer página da carteira.
2. Pela interface: acesse a página de **Transações** no menu lateral e clique no botão **+ Nova Transação**.

### Campos do formulário:
- **Carteira**: Selecione a qual carteira a operação pertence.
- **Ativo (Ticker)**: Digite o código do ativo (ex.: `PETR4`, `HGLG11`, `AAPL`, `BTC`). O sistema buscará automaticamente o ativo cadastrado no catálogo.
- **Tipo de Operação**: Escolha entre Compra, Venda, etc.
- **Data da Operação**: Data em que o negócio foi efetivamente executado na corretora.
- **Quantidade**: Número de papéis, cotas ou fração negociada.
- **Preço Unitário**: Preço de execução por unidade do ativo.
- **Custos / Taxas Operacionais**: Informe emolumentos da B3, taxa de corretagem, ISS e taxas de liquidação. Estes custos são somados ao custo de aquisição na compra (aumentando o preço médio) e deduzidos do valor de alienação na venda (reduzindo o lucro tributável).
- **Notas / Observações**: Campo opcional para referenciar o número da nota de corretagem ou estratégia adotada.

---

## 3. Edição e Exclusão de Transações

O SGI oferece total flexibilidade para correção de lançamentos:
1. Na lista da página **Transações**, localize a operação desejada utilizando os filtros de busca.
2. Clique no ícone de **Editar** (lápis) para corrigir valores, quantidades ou taxas.
3. Caso a operação tenha sido lançada incorretamente ou em duplicidade, clique no ícone de **Excluir** (lixeira).
4. Ao salvar ou excluir, o SGI recalcula instantaneamente toda a cadeia cronológica de preço médio, posições em aberto e apurações fiscais desde a data da transação modificada.

---

## 4. Filtros e Pesquisa Avançada

A tela de Transações conta com ferramentas poderosas de filtragem para auditoria e conferência:
- **Busca por Ticker**: Filtre todas as operações de um papel específico (ex.: apenas `VALE3`).
- **Filtro por Tipo**: Isole apenas compras, vendas ou proventos.
- **Intervalo de Datas**: Defina o período inicial e final para conferir um mês específico ou ano fiscal.
- **Ordenação**: Ordene cronologicamente por data da transação ou por valor financeiro total.
