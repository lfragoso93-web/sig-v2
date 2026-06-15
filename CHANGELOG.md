# Changelog - SIG v2

Todas as alteracoes relevantes do projeto sao documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Referencias Tecnicas] - Anotacoes para sprints futuras

### Fonte: https://www.traders.com.br/blog/posts/api-financeira-python-mercado-como-usar

Levantamento de APIs e tecnicas financeiras em Python com aproveitamento direto no SIG v2.

---

#### Sprint 5 (Cotacoes e Integracoes de Mercado) — referencias

**yfinance com sufixo `.SA` para acoes brasileiras**
- Acoes BR devem usar ticker com sufixo `.SA` (ex: `PETR4.SA`). Acoes internacionais nao usam sufixo.
- Revisar `quotes_service.py` para garantir padronizacao consistente do sufixo ao chamar yfinance.
- Exemplo:
  ```python
  import yfinance as yf
  ticker = yf.Ticker("PETR4.SA")
  hist = ticker.history(period="1mo")
  ```
- **Aplicacao:** `backend/app/services/quotes_service.py` — padronizar logica de montagem do ticker antes da chamada yfinance.

**Cache local com Parquet para historico de cotacoes**
- Salvar cotacoes historicas em `.parquet` e atualizar apenas incrementalmente reduz chamadas externas e melhora performance do `price_history_service.py`.
- Estrategia: verificar se ja existe historico local; se sim, buscar apenas datas ausentes; concatenar e salvar.
- **Aplicacao:** Sprint 5 e Sprint 8 (Historico Patrimonial).

---

#### Sprint 10 (Renda Fixa e Tesouro Direto) — referencias

**Tesouro Direto via CSV oficial (B3/Tesouro Nacional)**
- O Tesouro disponibiliza CSV publico com historico completo de precos e taxas de todos os titulos, atualizado diariamente. Nao depende de BRAPI nem yfinance.
- URL do arquivo:
  ```
  https://www.tesourodireto.com.br/json/br/com/b3/tesouro/tesouro-direto/1/TesouroDireto_HistoricoTaxaPreco.csv
  ```
- Exemplo de leitura:
  ```python
  import pandas as pd
  url = "https://www.tesourodireto.com.br/json/br/com/b3/tesouro/tesouro-direto/1/TesouroDireto_HistoricoTaxaPreco.csv"
  td = pd.read_csv(url, sep=';', encoding='latin-1', decimal=',', thousands='.')
  ```
- **Aplicacao:** `treasury_service.py` — usar como fonte primaria de preco atual e historico de titulos do Tesouro Direto.

**Banco Central via `python-bcb` (Selic, IPCA, CDI, cambio, IGPM)**
- Biblioteca `python-bcb` acessa o SGS (Sistema Gerenciador de Series Temporais) do Bacen de forma simples e oficial.
- Instalacao: `pip install python-bcb`
- Exemplos:
  ```python
  from bcb import sgs
  selic = sgs.get({'Selic': 11}, start='2020-01-01')
  ipca  = sgs.get({'IPCA': 433}, start='2020-01-01')
  cdi   = sgs.get({'CDI': 12}, start='2020-01-01')
  ptax  = sgs.get({'PTAX': 1}, start='2020-01-01')
  ```
- **Aplicacao:** `requirements.txt` / Sprint 10 (indexadores) / Sprint 12 (IRPF) / Sprint 5 (cambio PTAX).

---

#### Resumo de dependencias a adicionar nas sprints futuras

| Biblioteca | Sprint | Uso |
|---|---|---|
| `python-bcb` | Sprint 5 / Sprint 10 | Selic, IPCA, CDI, PTAX via Bacen |
| `pandas` (ja existe?) | Sprint 5 / Sprint 10 | Leitura do CSV do Tesouro e cache Parquet |
| `pyarrow` ou `fastparquet` | Sprint 5 / Sprint 8 | Cache de cotacoes em Parquet |

---

## [Unreleased] - Sprint 2 - 2026-06-15

### Correcao pos-auditoria (Bug Fix)

#### routers/transactions.py — Validacao de venda nao era executada
- **Problema identificado em auditoria:** O `transaction_service.py` refatorado na Sprint 2 nao era chamado em nenhum lugar. O router `transactions.py` implementava tudo diretamente com `AsyncSession`, ignorando o service e, consequentemente, toda a validacao de venda implementada.
- **Raiz do problema:** Service usa `Session` sincrona; router usa `AsyncSession`. Os dois nao eram compativeis e nao estavam conectados.
- **Solucao aplicada em `backend/app/routers/transactions.py`:**
  - Adicionado helper async `_calc_current_quantity(db, portfolio_id, ticker, exclude_tx_id)` usando `AsyncSession` + `select()`.
  - Parametro `exclude_tx_id` garante que ao **editar** uma venda existente, a propria transacao nao conta no calculo (evita falso bloqueio).
  - Adicionado helper `_validate_sell(db, portfolio_id, ticker, quantity, exclude_tx_id)` que levanta HTTP 400 com mensagem detalhada se `quantity > posicao_atual`.
  - `create_transaction`: chama `_validate_sell` antes do `db.add(tx)` quando `operation == "sell"`.
  - `update_transaction`: chama `_validate_sell` com `exclude_tx_id=transaction_id` antes do `db.commit()`.
- **Commit:** `4a4908e7` — fix(sprint2): integrar validacao de venda no router async (create e update)
- **Status:** Concluido.

---

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
  - `_calc_current_quantity(db, portfolio_id, ticker)` — versao sincrona para uso nos testes unitarios
  - `get_transaction`, `update_transaction` — funcoes que estavam faltando
- **Commit:** `c1434e56` — refactor(sprint2): alinhar transaction_service com modelo atual
- **Status:** Concluido (servico usado como referencia logica; router e a fonte de verdade async).

#### Validacao de venda
- **Commit:** `c1434e56` + `4a4908e7`
- **Status:** Ativa e funcional no router async.

---

### Testes (Tests)

#### test_transaction_service.py — Reescrita completa
- **Solucao aplicada:** Arquivo reescrito integralmente com `OperationType.buy/sell`, sem `TransactionType` ou `price_brl`. 13 cenarios cobrindo `_calc_average_price` e `_calc_current_quantity`.
- **Commit:** `18fbf392` — test(sprint2): reescrever testes de transaction_service com modelo atual
- **Status:** Concluido.

---

### Arquivos modificados na Sprint 2 (completo)

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `backend/app/services/transaction_service.py` | Refatoracao completa para modelo atual | `c1434e56` |
| `backend/tests/test_transaction_service.py` | Reescrita dos testes | `18fbf392` |
| `backend/app/routers/transactions.py` | Validacao de venda async integrada | `4a4908e7` |

---

### Sprint 2 encerrada. Todas as pendencias resolvidas. Proxima: Sprint 3.

---

## [Sessao anterior] - 2026-06-14

### Correcoes de bugs (Bug Fixes)

#### Resumo — Total Investido incorreto
- **Problema:** A coluna "Total Inv." na pagina Resumo exibia o mesmo valor de "Valor Atual", pois estava usando `current_value` em vez de `total_invested`.
- **Solucao aplicada:** `totalInvestido = quantidade * precoMedio` e `valorAtual = quantidade * precoAtual`.
- **Status:** Concluido.

#### Resumo — Remocao do seletor de carteiras duplicado
- **Solucao aplicada:** Seletor removido da pagina Resumo. Unico ponto e o dropdown na sidebar.
- **Status:** Concluido.

#### Patrimonio > Tesouro — Botao de novo lancamento removido
- **Status:** Concluido.

#### Transacoes — Botao "Nova transacao" removido
- **Status:** Concluido.

#### Modal de edicao — Unificacao com modal de novo lancamento
- **Solucao aplicada:** Unico componente `TransactionModal` com prop `mode: 'create' | 'edit'`.
- **Status:** Concluido.

#### Transacoes — Pagina reorganizada com tabelas por classe e grafico
- **Solucao aplicada:** Grafico de barras mensais + tabelas separadas por classe com accordion e busca interna.
- **Status:** Concluido.

#### Transacoes — Remocao do seletor de classe nos filtros globais
- **Commit:** `5602fae`
- **Status:** Concluido.

#### Transacoes — Bug: tabela some ao digitar no filtro interno do grupo
- **Causa raiz:** `if (groupList.length === 0) return null` desmontava o container inteiro.
- **Solucao aplicada:** Container sempre renderizado; conteudo vazio exibe mensagem inline.
- **Commit:** `5602fae`
- **Status:** Concluido.

---

### Refatoracao de navegacao

#### Patrimonio — Subpaginas removidas, pagina consolidada
- **Solucao aplicada:** Submenu removido da sidebar. Patrimonio e item direto apontando para `/carteira/patrimonio`.
- **Commit:** `408fa59`
- **Status:** Concluido.

---

### Arquivos modificados em 14/06/2026

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `frontend/src/components/layout/Sidebar.tsx` | Remocao de subpaginas e submenu de Patrimonio | `408fa59` |
| `frontend/src/pages/Transacoes.tsx` | Remocao do seletor de classes + correcao do bug de busca por grupo | `5602fae` |
