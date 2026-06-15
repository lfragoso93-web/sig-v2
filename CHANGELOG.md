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

## [Sprint 5] - 2026-06-15

### Objetivo
Tornar cotacoes mais robustas e previsiveis, estruturar o pipeline de precos com cache em camadas e implementar historico patrimonial real via snapshots diarios.

---

### Decisoes de arquitetura (Sprint 5)

#### Pipeline de cotacoes — 3 camadas (L1 → L2 → L3)

| Camada | Fonte | Escopo | TTL |
|---|---|---|---|
| L1 | `Asset.last_price` (banco) | Todos os ativos | Sem expirar — atualizado pelo scheduler |
| L2 | Cache em memoria (dict global) | Todos os ativos | 5 min |
| L3 | BRAPI / yfinance (API externa) | Nacionais / Internacionais | Sob demanda |

- Falha em L3 nao derruba nenhum endpoint; retorna `None` e loga o erro.
- Tipos nacionais: `ACAO`, `FII`, `ETF_NACIONAL`, `CRIPTO` → BRAPI.
- Tipos internacionais: `STOCK`, `ETF_INTERNACIONAL` → yfinance (sufixo `.SA` apenas para BR).
- `TESOURO_DIRETO`, `RENDA_FIXA` → sem cotacao de mercado, retornam `None`.

#### Snapshots diarios — `PortfolioSnapshot`

- Tabela `portfolio_snapshots` (migration `005`) armazena o valor de mercado calculado por carteira por dia.
- `backfill_snapshots()`: retroativo desde a 1a transacao, idempotente, pula fds e dias ja existentes.
- `refresh_today_snapshot()`: atualiza/cria o snapshot do dia atual (chamado pelo scheduler).
- `get_daily_evolution()` e `get_monthly_evolution()`: leituras para o frontend.
- Historico mensal do `performance_service` passou a usar snapshots reais (valor de mercado) em vez de custo acumulado.

---

### Alteracoes

#### asset_types.py — fonte unica de verdade para tipos de ativo
- `INTL_TYPES`, `BRAPI_TYPES`, `NO_QUOTE_TYPES` centralizados.
- Todos os services derivam de `asset_types.py`; nenhum define lista manual.
- **Commit:** `bb258df8`

#### Asset model + migration 004 — campo `last_price`
- Adicionado `last_price: Optional[Numeric]` no modelo `Asset`.
- Migration `004_add_last_price_to_assets.py`.
- **Commit:** `14f4b50e`

#### brapi.py — refatoracao da integracao BRAPI
- `get_quotes_bulk()`: busca em lote com fallback gracioso por ticker.
- `get_quote_single()`: busca individual.
- `get_historical_prices()`: OHLCV diario para historico.
- Sem `raise` em falha parcial; retorna lista com o que foi possivel obter.
- **Commit:** `315325e9`

#### price_history_service.py — historico OHLCV no banco
- `persist_daily_prices()`: INSERT ON CONFLICT DO NOTHING — idempotente.
- `get_price_at_date()`: busca preco de fechamento em data especifica.
- Suporte a `AssetType` nacionais e internacionais via yfinance.
- **Commit:** `9ea72604`

#### quotes_service.py — cache L1/L2/L3 unificado
- `get_prices(positions, db)`: entrada em lote `[{ticker, asset_type}]`, saida `{ticker: price}`.
- Ordem de resolucao: L1 banco → L2 memoria → L3 API.
- `invalidate(ticker)` e `invalidate_all()` para testes e forcas de refresh.
- **Commit:** `9015538d`

#### quote_service.py — `update_all_quotes(db)`
- Percorre todos os `Asset` do banco, busca cotacao via L3 e atualiza `Asset.last_price`.
- Usado pelo scheduler (job das 19h00) e disponivel como chamada manual.
- **Commit:** `c335b513`

#### PortfolioSnapshot model + migration 005
- Tabela `portfolio_snapshots`: `portfolio_id`, `snapshot_date`, `market_value`, `cost_basis`, `invested_total`, `unrealized_pnl`, `realized_pnl`, `total_pnl`, `return_pct`.
- Unique constraint `(portfolio_id, snapshot_date)`.
- **Commit:** `b4573326`

#### portfolio_snapshot_service.py — snapshots diarios
- `_build_positions_at(portfolio_id, D)`: reconstroi posicoes FIFO ate a data D.
- `_calc_totals(portfolio_id, D)`: valor de mercado por ticker via `get_price_at_date()`.
- `backfill_snapshots(db, portfolio_id, days_back)`: retroativo, idempotente, commit a cada 30 dias.
- `refresh_today_snapshot(db, portfolio_id)`: atualiza snapshot do dia atual.
- `get_daily_evolution(db, portfolio_id, days)`: serie diaria para grafico de linha.
- `get_monthly_evolution(db, portfolio_id, months)`: fechamento do ultimo dia util de cada mes.
- **Commit:** `4a8fbda6`

#### performance_service.py — refatoracao de cotacoes e historico
- `_fetch_price_brl()` substituido por `_fetch_prices_brl()` (lote via `quotes_service.get_prices(db=db)`).
- `calc_asset_performance()` recebe `prices_brl` pre-buscado — elimina N chamadas de API no loop.
- `_build_monthly_history()` substituido por `get_monthly_evolution()` — historico com valor de mercado real.
- `USD_TYPES` derivado de `INTL_TYPES` (fonte unica de verdade).
- **Commit:** `c8a57e83`

#### scheduler.py — jobs integrados
- Adicionado helper `_get_active_portfolio_ids()` (carteiras ativas com transacoes).
- Novo job `job_update_all_quotes_and_snapshots()` (19h00):
  - Passo 1: `update_all_quotes(db)` — atualiza `Asset.last_price`.
  - Passo 2: `refresh_today_snapshot(db, pid)` para cada carteira ativa.
- Roda 30min apos `persist_price_history` (18h30) para garantir que `AssetPrice` do dia esta no banco.
- Total: 6 jobs registrados.
- **Commit:** `f3a91f74`

#### routers/performance.py — endpoints de evolucao patrimonial
- `GET /{id}/evolution/daily?days=365` → serie diaria (`SnapshotPoint`).
- `GET /{id}/evolution/monthly?months=24` → fechamento mensal (`SnapshotPointMonthly`).
- `POST /{id}/evolution/backfill?days_back=N` → popula historico retroativo (`BackfillOut`).
- `HistoryPoint` substituido por `SnapshotPointMonthly` (campos de mercado real).
- `get_asset_performance` atualizado para passar `prices_brl` dict (nova assinatura).
- Helper `_assert_portfolio_owner()` adicionado.
- **Commit:** `239bcd92`

---

### Arquivos modificados na Sprint 5

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `backend/app/core/asset_types.py` | Novo — fonte unica de tipos de ativo | `bb258df8` |
| `backend/app/models/asset.py` | Adicionado campo `last_price` | `14f4b50e` |
| `backend/app/migrations/004_add_last_price_to_assets.py` | Nova migration | `14f4b50e` |
| `backend/app/integrations/brapi.py` | Refatorado — bulk, single, historical | `315325e9` |
| `backend/app/services/price_history_service.py` | Novo — OHLCV + get_price_at_date | `9ea72604` |
| `backend/app/services/quotes_service.py` | Novo — cache L1/L2/L3 unificado | `9015538d` |
| `backend/app/services/quote_service.py` | Refatorado — update_all_quotes | `c335b513` |
| `backend/app/models/portfolio_snapshot.py` | Novo modelo | `b4573326` |
| `backend/app/migrations/005_create_portfolio_snapshots.py` | Nova migration | `b4573326` |
| `backend/app/services/portfolio_snapshot_service.py` | Novo — backfill, refresh, evolucao | `4a8fbda6` |
| `backend/app/services/performance_service.py` | Refatorado — cotacoes em lote + historico real | `c8a57e83` |
| `backend/app/scheduler.py` | Integrado — 6 jobs, snapshots diarios | `f3a91f74` |
| `backend/app/routers/performance.py` | Novos endpoints de evolucao patrimonial | `239bcd92` |

---

### Checklist de deploy — Sprint 5

1. `alembic upgrade head` — aplica migrations `004` e `005`
2. `POST /portfolios/{id}/evolution/backfill` para cada carteira — popula historico retroativo
3. Scheduler das 19h00 passa a manter snapshots atualizados automaticamente

---

### Estado da base apos Sprint 5

Pipeline de cotacoes com 3 camadas de cache (banco → memoria → API). Historico patrimonial via snapshots diarios reais. Rentabilidade com historico de mercado. Scheduler com 6 jobs orquestrados. Frontend pode consumir evolucao diaria e mensal com valor de mercado real. Pronto para Sprint 6 (Proventos).

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
  - Corrigido: sem cotacao, `current_value`, `result_abs` e `result_pct` retornam `None`.
- **`recalc_positions`:**
  - `tx.fees or 0.0` adicionado para evitar crash quando `fees=None`.
  - Logica de venda consolidada: `total_cost -= avg_price * qty_tx` + `max(..., 0.0)`.
- **`calc_positions`:**
  - Logica de enriquecimento unificada com a mesma semantica de `enrich_with_prices`.
- **Commit:** `a73d9bd7`

#### routers/portfolios.py — Campos nullable no contrato da API
- `PositionItem`: `current_price`, `current_value`, `result_abs`, `result_pct` → `Optional[float] = None`.
- `SummaryResponse`: `total_current`, `result_abs`, `result_pct` → `Optional[float] = None`.
- **Commit:** `38bed9b3`

#### test_portfolio_service.py — Reescrita com criterios de aceite Sprint 4
- 23 cenarios cobrindo PM, vendas, fees, tipos de ativo, isolamento entre carteiras.
- **Commit:** `680b489f`

---

### Arquivos modificados na Sprint 4

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `backend/app/services/portfolio_service.py` | Correcao PM, enrich, recalc | `a73d9bd7` |
| `backend/app/routers/portfolios.py` | Campos nullable na API | `38bed9b3` |
| `backend/tests/test_portfolio_service.py` | Reescrita com criterios de aceite | `680b489f` |

---

## [Sprint 3] - 2026-06-15

### Refatoracao — Padronizacao total para AsyncSession

#### performance_service.py
- Migracao de `Session` para `AsyncSession`.
- **Commit:** `297b7e8b`

#### routers/performance.py
- Migracao para `AsyncSession`; lookup de ativo via `Transaction`.
- **Commit:** `07b89607`

---

## [Sprint 2] - 2026-06-15

### Correcao pos-auditoria
- `routers/transactions.py`: validacao de venda. **Commit:** `4a4908e7`
- `transaction_service.py`: alinhamento com modelo atual. **Commit:** `c1434e56`
- `test_transaction_service.py`: reescrita completa. **Commit:** `18fbf392`

---

## [Sessao anterior] - 2026-06-14

- Resumo: Total Investido e seletor duplicado corrigidos
- Transacoes: reorganizacao, modal unificado, bug de busca por grupo
- Patrimonio: subpaginas removidas da sidebar

| Arquivo | Commit |
|---|---|
| `frontend/src/components/layout/Sidebar.tsx` | `408fa59` |
| `frontend/src/pages/Transacoes.tsx` | `5602fae` |
