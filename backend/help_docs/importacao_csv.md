# Importação de Operações por Planilha CSV

O SGI disponibiliza um importador em lote por arquivo CSV para que você possa migrar seu histórico de notas de corretagem, extratos da B3 ou planilhas pessoais de forma ágil e segura.

---

## 1. Como Iniciar a Importação

1. No menu do usuário localizado na barra superior, clique na opção **Importar Extratos / Notas**.
2. O modal de importação será aberto, associado automaticamente à carteira que você estiver navegando no momento.
3. Você pode baixar o **Modelo canônico SGI** diretamente pelo link no modal para conferir o formato de colunas esperado.

---

## 2. Estrutura Canônica das Colunas (Modelo Oficial)

O importador exige as seguintes 9 colunas obrigatórias no cabeçalho do arquivo `.csv`:

| Coluna | Descrição | Valores Aceitos / Exemplo |
| :--- | :--- | :--- |
| `ticker` | Código do ativo negociado | `PETR4`, `MXRF11`, `IVVB11`, `AAPL`, `BTC` |
| `asset_type` | Classe do ativo no catálogo | `ACAO`, `FII`, `ETF_NACIONAL`, `ETF_INTERNACIONAL`, `BDR`, `STOCK`, `CRIPTO`, `TESOURO_DIRETO`, `RENDA_FIXA` |
| `operation` | Tipo da operação executada | `buy` (compra) ou `sell` (venda) |
| `quantity` | Quantidade de cotas ou frações negociadas | `100`, `50.5` |
| `price` | Preço unitário pago ou recebido | `25.50`, `80.00` |
| `date` | Data de execução no formato `AAAA-MM-DD` | `2024-01-15`, `2026-03-20` |
| `fees` | Custos operacionais, corretagem e emolumentos | `10.00`, `0.00` |
| `currency` | Moeda da transação | `BRL` (Real) ou `USD` (Dólar) |
| `notes` | Anotações ou número da nota (opcional) | `Compra inicial`, `Nota Corretora X` |

> **Exemplo de Linha CSV:**  
> `PETR4,ACAO,buy,100,25.50,2024-01-15,10.00,BRL,Compra inicial`

Para ativos de Renda Fixa com regras de indexação e vencimento, o arquivo suporta colunas complementares opcionais (como `fixed_income_product_type`, `fixed_income_rate_value`, `fixed_income_maturity_date`), presentes no modelo para download.

---

## 3. Validação Prévia e Pré-visualização

Ao selecionar ou arrastar o arquivo `.csv` para o importador:
1. O SGI realiza uma varredura completa das linhas antes de gravar qualquer dado no banco.
2. É exibida uma tabela de **Pré-visualização** indicando:
   - Linhas válidas prontas para gravação.
   - Detecção automática de ativos existentes no catálogo.
   - Linhas com inconformidades ou campos ausentes destacados para correção.
3. Se houver divergências (por exemplo, um cabeçalho ausente ou um ticker não reconhecido), o sistema indicará com precisão o motivo da inconsistência.

---

## 4. Confirmação e Integração ao Livro-Razão

Após conferir a pré-visualização:
1. Clique no botão **Confirmar Importação**.
2. Todas as transações válidas são integradas ao livro-razão da carteira em uma única operação segura.
3. A custódia, o preço médio histórico, a apuração de rentabilidade e os relatórios fiscais são recalculados e atualizados instantaneamente.
