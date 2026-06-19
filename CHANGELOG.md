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

## [Sessao] - 2026-06-18 (fim de dia)

### Hotfix — Tabela de ativos (PositionTable)

Sessao dedicada a correcao de tres bugs visuais e de dados na tabela de ativos do Resumo da carteira.

#### Problemas identificados

| # | Sintoma | Causa raiz |
|---|---|---|
| 1 | Cards grandes + linha de tabela aparecendo juntos | `md:hidden` / `hidden md:block` do Tailwind sem breakpoints configurados — ambos os blocos eram renderizados simultaneamente |
| 2 | Coluna "P. Atual" sempre exibindo `—` | `quotes_service.get_prices` retorna `None` para ativos sem cotacao recente na tabela `assets`; comportamento correto, mas revelou dependencia de L1 (DB cache) vazio |
| 3 | Coluna "Valor Atual" repetindo o "Total Investido" | `enrich_with_prices` fazia fallback `current_value = total_invested` quando `price is None`, mascarando a ausencia de cotacao |

#### Correcoes aplicadas

**Frontend — `frontend/src/components/resume/PositionTable.tsx`**
- Substituido `className="md:hidden"` / `className="hidden md:block"` por hook `useIsDesktop()` com `window.matchMedia('(min-width: 768px)')`
- Renderizacao condicional: `{!isDesktop && <cards>}` e `{isDesktop && <tabela>}` — nunca os dois simultaneamente
- Coluna "Valor Atual" na tabela desktop agora exibe `—` quando `current_price === null`
- Card mobile: "Valor Atual" exibe `—` quando `current_price === null` (nao mais repete investido)
- `hasQuote` corrigido: `current_price !== null && current_price !== undefined` (antes comparava com `average_price`)
- Chave React corrigida: `item.id ?? item.ticker` (antes podia usar `item.id` undefined)
- **Commit:** `f82c6dc3`

**Backend — `backend/app/services/portfolio_service.py`**
- `enrich_with_prices`: quando `price is None`, agora retorna `current_price=None` e `current_value=None` em vez de `current_value=total_invested`
- `get_portfolio_positions`: expoe `current_price=None` / `current_value=None` explicitamente no payload
- Calculo de alocacao e soma de `total_current` usa `current_value or total_invested` (fallback so para alocacao percentual, nao para exibicao)
- Adicionado campo `id` sintetico (`idx + 1`) em cada posicao para uso como chave React
- **Commit:** `25754acb`

**Backend — `backend/app/schemas/position.py`**
- `PositionOut.current_value` alterado de `float` para `Optional[float]` — reflete ausencia de cotacao
- `PositionOut.id` adicionado como `Optional[int]` — id sintetico para chave React
- **Commit:** `25754acb`

#### Comportamento apos os hotfixes

| Campo | Sem cotacao | Com cotacao |
|---|---|---|
| P. Atual | `—` | `R$ XX,XX` |
| Valor Atual | `—` | `R$ XX,XX` |
| Resultado | `—` | `+R$ X,XX (+X,XX%)` |
| Layout | Cards (mobile) | Tabela (desktop) — nunca ambos juntos |

#### Pendente (roadmap Sprint 7)

- Investigar por que `quotes_service` nao esta populando `Asset.last_price` para os ativos da carteira (L1 sempre vazio)
- Revisar logica de rentabilidade: calculo de resultado, variacao percentual e rentabilidade total
- Ver secao Sprint 7 em [ROADMAP_SPRINTS.md](./ROADMAP_SPRINTS.md)

---

## [Sessao] - 2026-06-15 (fim de dia)

### Manutencao e estabilizacao pos-upgrade

Sessao dedicada a limpeza de PRs obsoletos, correcao de bugs criticos de inicializacao do backend e atualizacao da infraestrutura Docker/CI.

#### PRs fechados (obsoletos)
- **PR #2** fechado — pacotes pip (`python-multipart`, `pytest`, `python-jose`) ja estavam atualizados na `main` com versoes mais recentes.
- **PR #3** fechado — Vite 5→8, Tailwind 3→4, TypeScript 5→6 ja aplicados diretamente na `main`.

#### PR mergeado
- **PR #4** mergeado (squash) — GitHub Actions core group: `checkout v6`, `setup-python v6`, `setup-node v6`, `dependency-review v5`. Commit: `450377b9`.

#### Correcoes de bugs — Backend

| Arquivo | Problema | Correcao | Commit |
|---|---|---|---|
| `backend/app/routers/auth.py` | `ImportError`: `get_password_hash` e `create_jwt_token` inexistentes em `security.py` (renomeados na migracao passlib→bcrypt nativo) | `get_password_hash` → `hash_password`; `create_jwt_token({...})` → `create_access_token(subject=str(...))` | `3f98e74f` |
| `backend/app/routers/portfolios.py` | `ModuleNotFoundError: No module named 'app.core.auth'` — modulo renomeado para `deps.py` | `from app.core.auth` → `from app.core.deps` | `d8bc50a5` |

#### Correcoes de infraestrutura

| Arquivo | Problema | Correcao | Commit |
|---|---|---|---|
| `frontend/Dockerfile` | `npm ci` falha sem `package-lock.json` no repositorio | Fallback condicional: `if [ -f package-lock.json ]; then npm ci; else npm install; fi` | `1b4eb493` |
| `frontend/package-lock.json` | Arquivo ausente — impedia builds reproduziveis | Gerado localmente e commitado | `8d7a99a9` |

#### Seguranca
- `reset_pwd.py` removido do repositorio — continha senha `Admin@123` em texto claro. Commit: `febaae6e`.
- ⚠️ Arquivo ainda presente no historico do git (commit `8d7a99a9`). Recomendado usar `git filter-repo` para limpeza completa e trocar a senha nos ambientes.

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
| L1 | `Asset.last_price` (banco) | Todos os ativos | 15 min (PRICE_TTL_SECONDS=900) |
| L2 | Cache em memoria (dict global) | Todos os ativos | 1 min (MEM_CACHE_TTL=60) |
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
