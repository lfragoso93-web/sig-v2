# Changelog - SIG v2

Todas as alteracoes relevantes do projeto sao documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Unreleased] - Sprint 2 - 2026-06-15

### Refatoracao (Refactor)

#### transaction_service.py — Alinhamento com modelo atual
- **Problema:** O servico usava campos legados (`asset_id`, `TransactionType`, `price_brl`, `transaction_date`) incompativeis com o modelo atual de `Transaction`.
- **Solucao aplicada:** Servico completamente reescrito para usar o modelo atual:
  - `ticker` (string direta, sem join em tabela `Asset`)
  - `operation` (`OperationType.buy` / `OperationType.sell`)
  - `date` (campo renomeado de `transaction_date`)
  - `price` (preco unico em BRL; campo `price_brl` removido)
  - Nenhum import de `Asset`, `TransactionType` ou `price_brl`
- **Funcoes adicionadas:**
  - `_calc_current_quantity(db, portfolio_id, ticker)` — calcula posicao atual em carteira para validacao de venda
  - `get_transaction(db, tx_id, user_id)` — busca transacao individual por ID
  - `update_transaction(db, tx_id, user_id, data)` — edicao de transacao existente
- **Commit:** `c1434e56` — refactor(sprint2): alinhar transaction_service com modelo atual
- **Status:** Concluido.

#### Validacao de venda em create_transaction
- **Problema:** Era possivel registrar uma venda com quantidade maior do que a posicao atual na carteira, sem qualquer aviso ou bloqueio.
- **Solucao aplicada:** `create_transaction` agora verifica `_calc_current_quantity` antes de inserir. Se `data.quantity > current_qty`, retorna HTTP 400 com mensagem clara indicando posicao disponivel e quantidade tentada.
- **Commit:** `c1434e56` — refactor(sprint2): alinhar transaction_service com modelo atual
- **Status:** Concluido.

---

### Testes (Tests)

#### test_transaction_service.py — Reescrita completa
- **Problema:** Os testes importavam `TransactionType` (inexistente no modelo atual) e nao cobriam o novo helper `_calc_current_quantity`.
- **Solucao aplicada:** Arquivo reescrito integralmente:
  - Todos os mocks usam `OperationType.buy` / `OperationType.sell`
  - Removida dependencia de `price_brl` — mocks usam apenas `price`
  - Adicionada classe `TestCalcCurrentQuantity` com 5 cenarios: compras puras, venda parcial, venda total, sem transacoes, venda maior que estoque
  - Adicionado teste `test_multiplas_compras_e_vendas` para validar PM apos ciclo compra-venda-compra
- **Commit:** `18fbf392` — test(sprint2): reescrever testes de transaction_service com modelo atual
- **Status:** Concluido.

---

### Arquivos modificados nesta sessao (Sprint 2)

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `backend/app/services/transaction_service.py` | Refatoracao completa para modelo atual | `c1434e56` |
| `backend/tests/test_transaction_service.py` | Reescrita dos testes | `18fbf392` |

---

### Todos os itens da Sprint 2 (sessao 15/06/2026) foram concluidos. Nenhuma pendencia em aberto.

---

## [Sessao anterior] - 2026-06-14

### Correcoes de bugs (Bug Fixes)

#### Resumo — Total Investido incorreto
- **Problema:** A coluna "Total Inv." na pagina Resumo exibia o mesmo valor de "Valor Atual", pois estava usando `current_value` (preco atual * quantidade) em vez de `total_invested` (preco medio * quantidade).
- **Solucao aplicada:** Separados os campos no calculo de posicao: `totalInvestido = quantidade * precoMedio` e `valorAtual = quantidade * precoAtual`. No frontend, cada coluna aponta para o campo correto da API.
- **Status:** Concluido.

#### Resumo — Remocao do seletor de carteiras duplicado
- **Problema:** A pagina Resumo exibia um seletor de carteiras proprio, causando confusao com o seletor global que ja existe na sidebar.
- **Solucao aplicada:** Seletor de carteiras removido da pagina Resumo. O unico ponto de selecao de carteira e o dropdown na sidebar.
- **Status:** Concluido.

#### Patrimonio > Tesouro — Botao de novo lancamento removido
- **Problema:** A subpagina de Tesouro Direto dentro de Patrimonio exibia um botao local `+ Novo Lancamento` que nao deveria existir.
- **Solucao aplicada:** Botao removido. Toda criacao de ativo passa exclusivamente pelo botao `+ Novo Lancamento` no header global da aplicacao.
- **Status:** Concluido.

#### Transacoes — Botao "Nova transacao" removido
- **Problema:** A pagina de Transacoes possuia um botao proprio `+ Nova transacao`, criando dois pontos de entrada para o mesmo fluxo.
- **Solucao aplicada:** Botao removido. O fluxo de criacao foi centralizado no header global.
- **Status:** Concluido.

#### Modal de edicao — Unificacao com modal de novo lancamento
- **Problema:** Existiam dois modais distintos: um para "Novo Lancamento" (header) e outro para edicao de transacoes existentes. Isso gerava inconsistencia visual e de comportamento.
- **Solucao aplicada:** Unificado em um unico componente `TransactionModal` com prop `mode: 'create' | 'edit'`. No modo edicao, o modal abre pre-preenchido com os dados da transacao via `initialData`. O contexto global `useTransactionModal` expoe `openCreate()` e `openEdit(transaction)`, chamados respectivamente pelo header e pelos botoes de edicao nas tabelas.
- **Status:** Concluido.

#### Transacoes — Pagina reorganizada com tabelas por classe e grafico
- **Problema:** A pagina de Transacoes listava todos os ativos em uma unica tabela misturada, sem separacao por classe e sem visao grafica de aportes.
- **Solucao aplicada:** Transacoes agora exibem:
  - Grafico de barras mensais no topo (Compras em verde / Vendas em rosa), identico ao modelo de referencia do sistema SIG v1.
  - Tabelas separadas por classe de ativo (Acoes, FIIs, ETFs Nacionais, ETFs Internacionais, Stocks, Tesouro Direto, Renda Fixa, Criptomoedas), cada uma com accordion expand/collapse e busca interna por ticker.
- **Status:** Concluido.

#### Transacoes — Remocao do seletor de classe nos filtros globais
- **Problema:** Os filtros globais da pagina de Transacoes incluiam um `<select>` para filtrar por classe de ativo, redundante pois as transacoes ja estao separadas por classe em tabelas proprias.
- **Solucao aplicada:** Select de classe removido de `frontend/src/pages/Transacoes.tsx`. Os filtros globais passaram a ser apenas: busca por ticker e toggle Todos / Compras / Vendas.
- **Commit:** `5602fae` — fix(transacoes): remover seletor de classes e corrigir bug de tabela sumindo ao buscar no grupo.
- **Status:** Concluido.

#### Transacoes — Bug: tabela some ao digitar no filtro interno do grupo
- **Problema:** Ao digitar no input de busca dentro do header de um grupo (ex: buscar "PETR" dentro da tabela de Acoes), o grupo inteiro desaparecia da tela. Ao apagar o texto, voltava. O bug ocorria em desktop e mobile.
- **Causa raiz:** O bloco `if (groupList.length === 0) return null` estava posicionado antes da renderizacao do container do grupo. Quando a busca interna filtrava todos os itens, o componente inteiro (incluindo header e input) era desmontado.
- **Solucao aplicada em `frontend/src/pages/Transacoes.tsx`:**
  - O container do grupo sempre e renderizado, independentemente do resultado do filtro interno.
  - O conteudo interno verifica `groupList`: se vazia, exibe mensagem `"Nenhum ticker encontrado neste grupo."` inline.
  - `handleGroupSearchChange` forca o grupo a ficar aberto ao digitar (`setOpenGroups → true`).
- **Commit:** `5602fae` — fix(transacoes): remover seletor de classes e corrigir bug de tabela sumindo ao buscar no grupo.
- **Status:** Concluido.

---

### Refatoracao de navegacao (Navigation Refactor)

#### Patrimonio — Subpaginas removidas, pagina consolidada
- **Problema:** Patrimonio tinha tres subpaginas separadas (Renda Variavel, Tesouro Direto, Renda Fixa) acessiveis por submenu na sidebar, causando confusao de navegacao nos usuarios.
- **Solucao aplicada em `frontend/src/components/layout/Sidebar.tsx`:**
  - Removido o array `NAV_PATRIMONIO_SUBS` com as rotas `/carteira/patrimonio/renda-variavel`, `/carteira/patrimonio/tesouro` e `/carteira/patrimonio/renda-fixa`.
  - Removido o bloco de submenu expansivel (accordion) do item Patrimonio na sidebar.
  - Patrimonio agora e um item de navegacao direto, sem filhos, apontando para `/carteira/patrimonio`.
  - Removidos imports nao utilizados: `TrendingDown`, `Building2`, `Banknote`, `ChevronDown` (do menu patrimonio) e estado `patrimonioOpen`.
- **Resultado:** O usuario ve Patrimonio como um item simples na sidebar. A pagina `PatrimonioPage` exibe o conteudo consolidado: KPIs, alocacao por classe, grafico donut e tabela de posicoes filtrada por classe, com cada classe de renda variavel exibida separadamente.
- **Commit:** `408fa59` — fix(nav): remover subpaginas de Patrimonio da sidebar e deixar apenas Patrimonio consolidado.
- **Status:** Concluido.

---

### Arquivos modificados em 14/06/2026

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `frontend/src/components/layout/Sidebar.tsx` | Remocao de subpaginas e submenu de Patrimonio | `408fa59` |
| `frontend/src/pages/Transacoes.tsx` | Remocao do seletor de classes + correcao do bug de busca por grupo | `5602fae` |
