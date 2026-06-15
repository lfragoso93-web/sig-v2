# Changelog - SIG v2

Todas as alteracoes relevantes do projeto sao documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Unreleased] - 2026-06-14

### Correcoes de bugs (Bug Fixes)

#### Resumo — Total Investido incorreto
- **Problema:** A coluna "Total Inv." na pagina Resumo exibia o mesmo valor de "Valor Atual", pois estava usando `current_value` (preco atual * quantidade) em vez de `total_invested` (preco medio * quantidade).
- **Solucao orientada:** Separar os campos no calculo de posicao: `totalInvestido = quantidade * precoMedio` e `valorAtual = quantidade * precoAtual`. No frontend, garantir que cada coluna aponte para o campo correto da API.
- **Arquivos afetados:** logica de calculo de posicoes no backend e coluna de exibicao em `PositionTable`.

#### Resumo — Remocao do seletor de carteiras duplicado
- **Problema:** A pagina Resumo exibia um seletor de carteiras proprio, causando confusao com o seletor global que ja existe na sidebar.
- **Solucao:** Seletor de carteiras removido da pagina Resumo. O unico ponto de selecao de carteira e o dropdown na sidebar.

#### Patrimonio > Tesouro — Botao de novo lancamento removido
- **Problema:** A subpagina de Tesouro Direto dentro de Patrimonio exibia um botao local `+ Novo Lancamento` que nao deveria existir.
- **Solucao:** Botao removido da pagina de Tesouro. Toda criacao de ativo passa exclusivamente pelo botao `+ Novo Lancamento` no header global da aplicacao.

#### Transacoes — Botao "Nova transacao" removido
- **Problema:** A pagina de Transacoes possuia um botao proprio `+ Nova transacao`, criando dois pontos de entrada para o mesmo fluxo.
- **Solucao:** Botao removido. O fluxo de criacao foi centralizado no header global.

#### Modal de edicao — Unificacao com modal de novo lancamento
- **Problema:** Existiam dois modais distintos: um para "Novo Lancamento" (header) e outro para edicao de transacoes existentes. Isso gerava inconsistencia visual e de comportamento.
- **Solucao orientada:** Unificar em um unico componente `TransactionModal` com prop `mode: 'create' | 'edit'`. No modo edicao, o modal abre pre-preenchido com os dados da transacao via `initialData`. O contexto global `useTransactionModal` expoe `openCreate()` e `openEdit(transaction)`, chamados respectivamente pelo header e pelos botoes de edicao nas tabelas.

#### Transacoes — Pagina reorganizada com tabelas por classe e grafico
- **Problema:** A pagina de Transacoes listava todos os ativos em uma unica tabela misturada, sem separacao por classe e sem visao grafica de aportes.
- **Solucao:** Transacoes agora exibem:
  - Grafico de barras mensais no topo (Compras em verde / Vendas em rosa), identico ao modelo de referencia do sistema SIG v1.
  - Tabelas separadas por classe de ativo (Acoes, FIIs, ETFs Nacionais, ETFs Internacionais, Stocks, Tesouro Direto, Renda Fixa, Criptomoedas), cada uma com accordion expand/collapse e busca interna por ticker.

#### Transacoes — Remocao do seletor de classe nos filtros globais
- **Problema:** Os filtros globais da pagina de Transacoes incluiam um `<select>` para filtrar por classe de ativo, o que era redundante dado que as transacoes ja estao separadas por classe em tabelas proprias.
- **Correcao aplicada:** Select de classe removido de `frontend/src/pages/Transacoes.tsx`. Os filtros globais passaram a ser apenas: busca por ticker e toggle Todos / Compras / Vendas.
- **Commit:** `5602fae` — fix(transacoes): remover seletor de classes e corrigir bug de tabela sumindo ao buscar no grupo.

#### Transacoes — Bug: tabela some ao digitar no filtro interno do grupo
- **Problema:** Ao digitar no input de busca dentro do header de um grupo (ex: buscar "PETR" dentro da tabela de Acoes), o grupo inteiro desaparecia da tela. Ao apagar o texto, voltava. O bug ocorria em desktop e mobile.
- **Causa raiz:** O bloco `if (groupList.length === 0) return null` estava posicionado antes da renderizacao do container do grupo. Quando a busca interna filtrava todos os itens, o componente inteiro (incluindo header e input) era desmontado, dando a impressao de que a tabela havia sumido.
- **Correcao aplicada em `frontend/src/pages/Transacoes.tsx`:**
  - O container do grupo (card com header e input de busca) passa a ser sempre renderizado, independentemente do resultado do filtro interno.
  - O conteudo interno (tabela ou cards) verifica `groupList`: se vazia, exibe mensagem `"Nenhum ticker encontrado neste grupo."` inline.
  - `handleGroupSearchChange` agora forca o grupo a ficar aberto ao digitar (`setOpenGroups → true`), evitando busca invisivel em grupo colapsado.
- **Commit:** `5602fae` — fix(transacoes): remover seletor de classes e corrigir bug de tabela sumindo ao buscar no grupo.

---

### Refatoracao de navegacao (Navigation Refactor)

#### Patrimonio — Subpaginas removidas, pagina consolidada
- **Problema:** Patrimonio tinha tres subpaginas separadas (Renda Variavel, Tesouro Direto, Renda Fixa) acessiveis por submenu na sidebar, causando confusao de navegacao nos usuarios.
- **Solucao aplicada em `frontend/src/components/layout/Sidebar.tsx`:**
  - Removido o array `NAV_PATRIMONIO_SUBS` com as rotas `/carteira/patrimonio/renda-variavel`, `/carteira/patrimonio/tesouro` e `/carteira/patrimonio/renda-fixa`.
  - Removido o bloco de submenu expansivel (accordion) do item Patrimonio na sidebar.
  - Patrimonio agora e um item de navegacao direto, sem filhos, apontando para `/carteira/patrimonio`.
  - Removidos imports nao utilizados: `TrendingDown`, `Building2`, `Banknote`, `ChevronDown` (do menu patrimonio) e estado `patrimonioOpen`.
- **Resultado:** O usuario ve Patrimonio como um item simples na sidebar. A pagina `PatrimonioPage` ja exibe o conteudo consolidado: KPIs, alocacao por classe, grafico donut e tabela de posicoes filtrada por classe.
- **Commit:** `408fa59` — fix(nav): remover subpaginas de Patrimonio da sidebar e deixar apenas Patrimonio consolidado.

---

### Arquivos modificados nesta sessao

| Arquivo | Tipo de alteracao |
|---|---|
| `frontend/src/components/layout/Sidebar.tsx` | Remocao de subpaginas e submenu de Patrimonio |
| `frontend/src/pages/Transacoes.tsx` | Remocao do seletor de classes + correcao do bug de busca por grupo |

---

### Pendencias identificadas (nao implementadas nesta sessao)

Os itens abaixo foram diagnosticados e documentados, mas requerem acesso aos arquivos de calculo de posicao e ao componente do modal de lancamento para implementacao:

- [ ] Corrigir campo `Total Investido` no backend/frontend (usar `preco_medio * quantidade`, nao `preco_atual * quantidade`).
- [ ] Unificar modal de Novo Lancamento e edicao em componente unico com `mode: 'create' | 'edit'`.
- [ ] Remover botao `+ Novo Lancamento` da subpagina de Tesouro Direto (arquivo de subpagina nao localizado nesta sessao — pode ter sido removido junto com as subpaginas de navegacao).
