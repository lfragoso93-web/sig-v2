# Importação de Operações por Planilha CSV

O SGI disponibiliza um importador em lote por arquivo CSV para que você possa migrar seu histórico de notas de corretagem, extratos da B3 ou planilhas pessoais de forma ágil e segura.

---

## 1. Como Iniciar a Importação

1. No menu do usuário localizado na barra superior, clique na opção **Importar CSV**.
2. O modal de importação será aberto, associado automaticamente à carteira que você estiver navegando no momento.
3. Você pode baixar o **Modelo canônico SGI** diretamente pelo link no modal para conferir o formato de colunas esperado.

---

## 2. Estrutura das Colunas do Arquivo CSV

Para garantir leitura imediata e sem erros, seu arquivo deve conter um cabeçalho com as seguintes colunas essenciais:

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| `data` | Data de execução do negócio no formato `AAAA-MM-DD` ou `DD/MM/AAAA` | `2026-03-15` ou `15/03/2026` |
| `tipo` | Tipo da operação: `COMPRA`, `VENDA`, `DIVIDENDO`, `JCP`, etc. | `COMPRA` |
| `ticker` | Código do ativo negociado | `PETR4`, `MXRF11`, `IVVB11` |
| `quantidade` | Quantidade de cotas ou ações (número positivo) | `100` |
| `preco` | Preço unitário de execução | `38.50` |
| `taxas` | Custos operacionais, corretagem e emolumentos (opcional) | `1.25` |
| `notas` | Anotações ou identificador da nota de corretagem (opcional) | `Nota 12345 Corretora X` |

> **Dica**: O importador aceita tanto ponto (`.`) quanto vírgula (`,`) como separador decimal para valores monetários e quantidades.

---

## 3. Validação Prévia e Pré-visualização

Ao selecionar ou arrastar o arquivo `.csv` para o importador:
1. O SGI realiza uma varredura completa das linhas antes de gravar qualquer dado no banco.
2. É exibida uma tabela de **Pré-visualização** indicando:
   - Linhas válidas prontas para gravação.
   - Detecção automática de ativos existentes no catálogo.
   - Linhas com inconformidades ou campos ausentes destacados em amarelo/vermelho.
3. Se houver divergências (por exemplo, um ticker não reconhecido ou uma data inválida), o sistema indicará com precisão o número da linha e o motivo da inconsistência.

---

## 4. Confirmação e Integração ao Livro-Razão

Após conferir a pré-visualização:
1. Clique no botão **Confirmar Importação**.
2. Todas as transações válidas são integradas ao livro-razão da carteira em uma única operação segura.
3. A custódia, o preço médio histórico, a apuração de rentabilidade e os relatórios fiscais são recalculados e atualizados instantaneamente.
