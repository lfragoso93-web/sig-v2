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

## [Sprint 6] - 2026-06-15

### Objetivo
Entregar proventos confiaveis para a pagina de Proventos: proventos dos ativos da carteira com valor por unidade, valor total pelo usuario, separados em recebidos e futuros. Frontend conectado ao backend com filtros, historico e sincronizacao manual.

---

### Decisoes de modelagem (Sprint 6)

#### Modelo de dois niveis — mantido e consolidado

| Tabela | Papel |
|---|---|
| `asset_dividends` | Provento global do ativo (ex_date, payment_date, value_per_unit, source). Alimentado pelo backfill via BRAPI/yfinance. |
| `dividends` | Provento da carteira especifica. Vincula portfolio + asset_dividend. Armazena quantity (cotas na data-ex), total_value e net_value calculados, status (RECEBIDO/A_RECEBER). |

#### Regras de calculo
- `total_value = quantity * value_per_unit`
- `net_value = total_value * 0.85` para JCP (IR 15%); `= total_value` para os demais
- `status = RECEBIDO` se `payment_date <= hoje`; caso contrario `A_RECEBER`
- `quantity` = posicao liquida (compras - vendas) na data-ex, calculada a partir de `Transaction` por `(portfolio_id, ticker, date <= ex_date)`

#### Tipos sem proventos via API (SKIP_TYPES)
- `CRIPTO`, `TESOURO_DIRETO`, `RENDA_FIXA` — ignorados silenciosamente pelo backfill

---

### Alteracoes — Backend

#### dividend_backfill_service.py — correcoes criticas
- **`_net_qty_on_date`:** corrigido para filtrar por `(portfolio_id, ticker, date)` — `Transaction` nao tem `asset_id`.
- **`_portfolios_with_asset`:** renomeado para `_portfolios_with_ticker`; busca por `ticker` em vez de `asset_id`.
- **`_upsert_portfolio_dividend`:** assinatura atualizada para receber `ticker`.
- **Tipos alinhados com `asset_types.py`:** `YF_TYPES = INTL_TYPES` (importado); `SKIP_TYPES` consolidado.
- **`OperationType.buy`:** comparacao via enum em vez de string livre.
- **Commit:** `73538f57`

#### proventos_service.py — reescrita completa
- Migrado de `Session` sincrona + `db.query()` para `AsyncSession` + `select()`.
- Removidos imports de schemas inexistentes (`app.schemas.dividend`).
- Retorna dicts puros — o router serializa.
- **Funcoes disponiveis:**
  - `get_summary(db, portfolio_id)` — total_recebido, total_a_receber, total_12m, media_mensal_12m
  - `list_items(db, portfolio_id, status, year, asset_type, page, page_size)` — listagem paginada com todos os campos
  - `get_monthly_history(db, portfolio_id, status, asset_type)` — historico por ano/mes
  - `get_distribution(db, portfolio_id, months)` — distribuicao percentual por ativo
- **Commit:** `75790b79`

#### routers/proventos.py — reescrita completa
- Migrado de sincrono para `async def` + `AsyncSession`.
- Removido prefixo `/api/v1` hardcoded (gerenciado pelo `main.py`).
- Removidos schemas inexistentes; resposta e o dict puro do service.
- Validacao de `status` via `DividendStatus` enum — retorna 422 com mensagem clara.
- **Endpoints disponibilizados:**
  - `GET /portfolios/{id}/proventos/summary`
  - `GET /portfolios/{id}/proventos` (filtros: status, year, asset_type, page)
  - `GET /portfolios/{id}/proventos/historico-mensal`
  - `GET /portfolios/{id}/proventos/distribuicao`
- **Commit:** `ff41314a`

#### routers/dividends.py — novo endpoint de sync manual
- **`POST /portfolios/{id}/dividends/sync`:** busca todos os tickers distintos da carteira via `Transaction` e dispara um `BackgroundTask` por ticker chamando `_run_backfill`. Retorna 202 Accepted com lista de tickers enfileirados.
- Reutiliza `_run_backfill` (sessao independente, mesmo padrao de `transactions.py`).
- **Commit:** `d2e7b5d5`

---

### Alteracoes — Frontend

#### frontend/src/services/proventosService.ts
- `ProventosSummary` alinhada com backend: `total_recebido`, `total_a_receber`, `total_12m`, `media_mensal_12m`
- `getDistribution` → `getDistribuicao`; URL corrigida para `/proventos/distribuicao`
- `getEvolucao` removido (endpoint nao existe no backend)
- `getList` agora aponta para `/portfolios/{id}/proventos`; retorna `ProventosListResponse` paginado
- Adicionado `sync()` → `POST /portfolios/{id}/dividends/sync`
- **Commit:** `c8ed7f85`

#### frontend/src/hooks/useProventos.ts
- `useProventosDistribution` renomeado para `useProventosDistribuicao`
- `useProventosEvolucao` removido
- `useProventosList` atualizado para receber params object e retornar `ProventosListResponse`
- Adicionado `useSyncProventos` — mutation que invalida todas as queries de proventos ao completar
- **Commit:** `a6b7ffef`

#### frontend/src/pages/ProventosPage.tsx
- KPIs corretos: `total_recebido`, `total_a_receber`, `total_12m`, `media_mensal_12m` (removido `yield_on_cost` inexistente)
- `ACAO_NACIONAL` corrigido para `ACAO` no filtro de tipo de ativo
- Toggle de status: **Todos / Recebidos / A Receber**
- Botao **Sincronizar proventos** com spinner via `useSyncProventos`
- `lista?.items` passado para `MeusProventosTable` (resposta paginada)
- Rodape com contador de proventos listados
- **Commit:** `670fc7bb`

---

### Arquivos modificados na Sprint 6

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `backend/app/services/dividend_backfill_service.py` | Correcao critica — ticker em vez de asset_id; alinhamento tipos | `73538f57` |
| `backend/app/services/proventos_service.py` | Reescrita — AsyncSession, sem schemas externos | `75790b79` |
| `backend/app/routers/proventos.py` | Reescrita — async, 4 endpoints funcionais | `ff41314a` |
| `backend/app/routers/dividends.py` | Novo endpoint POST /sync | `d2e7b5d5` |
| `frontend/src/services/proventosService.ts` | Tipos e URLs alinhados com backend | `c8ed7f85` |
| `frontend/src/hooks/useProventos.ts` | Hooks alinhados + useSyncProventos | `a6b7ffef` |
| `frontend/src/pages/ProventosPage.tsx` | Pagina conectada — filtros, KPIs, sync | `670fc7bb` |

---

### Contrato dos endpoints de proventos

| Endpoint | Resposta |
|---|---|
| `GET /proventos/summary` | `{ total_recebido, total_a_receber, total_12m, media_mensal_12m }` |
| `GET /proventos` | `{ total, page, page_size, items: [{ticker, value_per_unit, quantity, total_value, net_value, status, ex_date, payment_date, ...}] }` |
| `GET /proventos/historico-mensal` | `[{ year, months: [null|float x12], total, media }]` |
| `GET /proventos/distribuicao` | `[{ ticker, asset_type, total, percentage }]` |
| `POST /dividends/sync` | `{ message, queued, tickers }` — 202 Accepted |

---

### Estado da base apos Sprint 6

Backend e frontend de proventos totalmente funcionais. Backfill corrigido para usar ticker. Frontend conectado via service + hooks alinhados. Pagina exibe KPIs, historico mensal, lista filtrada e botao de sync. Pronto para Sprint 7 (Rentabilidade).

---

## [Sprint 5] - 2026-06-15

### Objetivo
Tornar cotacoes mais robustas e previsiveis, estruturar o pipeline de precos com cache em camadas e implementar historico patrimonial real via snapshots diarios.

---

### Decisoes de arquitetura (Sprint 5)

#### Pipeline de cotacoes — 3 camadas (L1 -> L2 -> L3)

| Camada | Fonte | Escopo | TTL |
|---|---|---|---|
| L1 | `Asset.last_price` (banco) | Todos os ativos | Sem expirar — atualizado pelo scheduler |
| L2 | Cache em memoria (dict global) | Todos os ativos | 5 min |
| L3 | BRAPI / yfinance (API externa) | Nacionais / Internacionais | Sob demanda |

- Falha em L3 nao derruba nenhum endpoint; retorna `None` e loga o erro.
- Tipos nacionais: `ACAO`, `FII`, `ETF_NACIONAL`, `CRIPTO` -> BRAPI.
- Tipos internacionais: `STOCK`, `ETF_INTERNACIONAL` -> yfinance.
- `TESOURO_DIRETO`, `RENDA_FIXA` -> sem cotacao de mercado, retornam `None`.

#### Snapshots diarios — `PortfolioSnapshot`

- Tabela `portfolio_snapshots` (migration `005`) armazena o valor de mercado calculado por carteira por dia.
- `backfill_snapshots()`: retroativo desde a 1a transacao, idempotente, pula fds e dias ja existentes.
- `refresh_today_snapshot()`: atualiza/cria o snapshot do dia atual (chamado pelo scheduler).

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

## [Sprint 4] - 2026-06-15

### Objetivo
Consolidar o nucleo patrimonial como fonte confiavel do sistema.

### Alteracoes

| Arquivo | Tipo de alteracao | Commit |
|---|---|---|
| `backend/app/services/portfolio_service.py` | Correcao PM, enrich, recalc | `a73d9bd7` |
| `backend/app/routers/portfolios.py` | Campos nullable na API | `38bed9b3` |
| `backend/tests/test_portfolio_service.py` | Reescrita com criterios de aceite | `680b489f` |

---

## [Sprint 3] - 2026-06-15

### Refatoracao — Padronizacao total para AsyncSession

| Arquivo | Commit |
|---|---|
| `backend/app/services/performance_service.py` | `297b7e8b` |
| `backend/app/routers/performance.py` | `07b89607` |

---

## [Sprint 2] - 2026-06-15

### Correcao pos-auditoria

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
