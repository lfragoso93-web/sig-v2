# Changelog - SIG v2

Todas as alteracoes relevantes do projeto sao documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Referencias Tecnicas] - Anotacoes para sprints futuras

### Fonte: https://www.traders.com.br/blog/posts/api-financeira-python-mercado-como-usar

---

#### Sprint 5 (Cotacoes e Integracoes de Mercado) — referencias

**yfinance com sufixo `.SA` para acoes brasileiras**
- Acoes BR: ticker com sufixo `.SA` (ex: `PETR4.SA`). Internacionais sem sufixo.
- **Aplicacao:** `backend/app/services/quotes_service.py`

**Cache local com Parquet para historico de cotacoes**
- Salvar cotacoes em `.parquet` e atualizar apenas incrementalmente.
- **Aplicacao:** Sprint 5 e Sprint 8 (Historico Patrimonial).

---

#### Sprint 10 (Renda Fixa e Tesouro Direto) — referencias

**Tesouro Direto via CSV oficial (B3/Tesouro Nacional)**
- URL: `https://www.tesourodireto.com.br/json/br/com/b3/tesouro/tesouro-direto/1/TesouroDireto_HistoricoTaxaPreco.csv`
- **Aplicacao:** `treasury_service.py`

**Banco Central via `python-bcb` (Selic, IPCA, CDI, cambio, IGPM)**
- Instalacao: `pip install python-bcb`
- **Aplicacao:** Sprint 10 / Sprint 12 (IRPF) / Sprint 5 (cambio PTAX).

---

#### Resumo de dependencias a adicionar nas sprints futuras

| Biblioteca | Sprint | Uso |
|---|---|---|
| `python-bcb` | Sprint 5 / Sprint 10 | Selic, IPCA, CDI, PTAX via Bacen |
| `pyarrow` ou `fastparquet` | Sprint 5 / Sprint 8 | Cache de cotacoes em Parquet |

---

## [Sprint 4] - 2026-06-15

### Objetivo
Consolidar o nucleo patrimonial como fonte confiavel do sistema.

---

### Decisoes de modelagem confirmadas (Sprint 4)

#### Regras de Preco Medio Ponderado

| Evento | Comportamento |
|---|---|
| Compra | PM recalculado: `(custo_atual + qty*preco + fees) / (qty_atual + qty)` |
| Venda | PM invariante. `qty` diminui. `total_cost -= PM * qty_vendida`. |
| `fees` de venda | NAO entram no PM. Afetam apenas lucro realizado. |
| Posicao zerada | `qty <= 1e-9` — some da carteira (renda variavel E Tesouro Direto). |
| Sem cotacao | `current_price=None`, `current_value=None`, `result_abs=None`, `result_pct=None`. Nunca usar PM como fallback. |

---

### Alteracoes

#### portfolio_service.py — Correcoes e consolidacao
- **Removido:** import morto `from sqlalchemy.orm import Session`.
- **`calc_raw_positions`:**
  - Adicionado `max(..., 0.0)` em `total_cost` e `qty` apos venda (guard contra float drift).
  - Ordem de transacoes agora usa `.order_by(date.asc(), id.asc())` para desempate deterministico.
  - `fees=None` tratado com `float(tx.fees or 0.0)`.
- **`enrich_with_prices`:**
  - Corrigido: sem cotacao, `current_value`, `result_abs` e `result_pct` retornam `None` (antes retornavam `0.0` e usavam `avg_price` como preco efetivo — violacao do criterio de aceite).
- **`recalc_positions`:**
  - `tx.fees or 0.0` adicionado para evitar crash quando `fees=None`.
  - Logica de venda consolidada: `total_cost -= avg_price * qty_tx` + `max(..., 0.0)` em ambos os campos.
- **`calc_positions`:**
  - Logica de enriquecimento unificada com a mesma semantica de `enrich_with_prices` (campos `None` quando sem cotacao).
- **Commit:** `a73d9bd7` — refactor(sprint4): corrigir enrich_with_prices, recalc_positions e remover import Session morto
- **Status:** Concluido.

#### routers/portfolios.py — Campos nullable no contrato da API
- **`PositionItem`:** `current_price`, `current_value`, `result_abs`, `result_pct` agora `Optional[float] = None`.
- **`SummaryResponse`:** `total_current`, `result_abs`, `result_pct` e aliases (`total_patrimonio`, `lucro_total`, etc.) agora `Optional[float] = None`.
- **`portfolio_summary`:** recalcula `result_abs`/`result_pct` usando apenas ativos com cotacao disponivel; retorna `None` se nenhum ativo tem cotacao.
- **Commit:** `38bed9b3` — refactor(sprint4): ajustar PositionItem e SummaryResponse para campos nullable
- **Status:** Concluido.

#### test_portfolio_service.py — Reescrita com criterios de aceite Sprint 4
- **Cenarios adicionados:**
  - `test_venda_mais_barata_nao_altera_pm` — venda com prejuizo nao muda PM
  - `test_taxa_de_venda_nao_entra_no_pm` — fees de venda nao afetam custo restante
  - `test_compra_venda_parcial_segunda_compra` — PM correto apos ciclo completo
  - `test_tesouro_direto_calcula_como_cotas` — Tesouro controlado por qtd de cotas
  - `test_isolamento_entre_carteiras` — posicoes de carteiras diferentes sao independentes
  - `test_sem_cotacao_todos_campos_none` — `current_value`, `result_abs`, `result_pct` sao `None`
  - `test_nao_usa_avg_como_cotacao` — `current_value` e `None` sem cotacao (nao usa PM)
  - `test_mix_com_e_sem_cotacao` — ativos com e sem cotacao na mesma lista
  - `test_cotacao_zerada_nao_divide_por_zero` — guard de divisao por zero
  - Novos tipos em `TestNormalizeType`: STOCK, STOCKS, FII, TESOURO_DIRETO, CRIPTOMOEDA
- **Commit:** `680b489f` — test(sprint4): reescrever testes de portfolio_service
- **Status:** Concluido.

---

### Arquivos modificados na Sprint 4

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `backend/app/services/portfolio_service.py` | Correcao PM, enrich, recalc, import morto | `a73d9bd7` |
| `backend/app/routers/portfolios.py` | Campos nullable na API | `38bed9b3` |
| `backend/tests/test_portfolio_service.py` | Reescrita com criterios de aceite | `680b489f` |

---

### Estado da base apos Sprint 4

O nucleo patrimonial esta consolidado como fonte confiavel. PM ponderado correto, posicoes zeradas removidas, fallback de cotacao eliminado, contrato da API com campos nullable, testes cobrindo todos os criterios de aceite. Pronto para Sprint 5 (Cotacoes e Integracoes de Mercado).

---

## [Sprint 3] - 2026-06-15

### Refatoracao — Padronizacao total para AsyncSession

#### performance_service.py
- Migracao de `Session` para `AsyncSession`; todas as queries com `await db.execute(select(...))`.
- **Commit:** `297b7e8b`

#### routers/performance.py
- Migracao para `AsyncSession`; lookup de ativo via `Transaction` em vez de `Asset`.
- **Commit:** `07b89607`

| Arquivo | Commit |
|---|---|
| `backend/app/services/performance_service.py` | `297b7e8b` |
| `backend/app/routers/performance.py` | `07b89607` |

---

## [Sprint 2] - 2026-06-15

### Correcao pos-auditoria
- `routers/transactions.py`: validacao de venda integrada com helpers async. **Commit:** `4a4908e7`
- `transaction_service.py`: alinhamento com modelo atual. **Commit:** `c1434e56`
- `test_transaction_service.py`: reescrita completa. **Commit:** `18fbf392`

| Arquivo | Commit |
|---|---|
| `backend/app/services/transaction_service.py` | `c1434e56` |
| `backend/tests/test_transaction_service.py` | `18fbf392` |
| `backend/app/routers/transactions.py` | `4a4908e7` |

---

## [Sessao anterior] - 2026-06-14

- Resumo: Total Investido e seletor duplicado corrigidos
- Transacoes: reorganizacao, modal unificado, bug de busca por grupo
- Patrimonio: subpaginas removidas da sidebar

| Arquivo | Commit |
|---|---|
| `frontend/src/components/layout/Sidebar.tsx` | `408fa59` |
| `frontend/src/pages/Transacoes.tsx` | `5602fae` |
