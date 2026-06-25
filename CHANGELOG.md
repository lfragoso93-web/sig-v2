# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Unreleased] — branch `stable-15jun`

### Corrigido — Tesouro Direto & Cripto (25/06/2026)

**Backend — `brapi.py`**
- `fetch_treasury_indicators`: adicionada **3ª tentativa de fallback** via `api.radaropcoes.com` quando BRAPI falha completamente
- `fetch_treasury_indicators`: token inválido/expirado (`400/401/403`) agora loga o status code explicitamente e cai no fallback `/list` sem lançar exceção
- `fetch_treasury_indicators`: fluxo agora tem **3 camadas em cascata**:
  1. `/v2/treasury/indicators` — somente se `BRAPI_TOKEN` configurado e retornar 2xx
  2. `/v2/treasury/list` — plano free, sempre tentado como primeiro fallback
  3. `api.radaropcoes.com` — fallback externo gratuito com dados em tempo real
- `fetch_treasury_prices`: continua usando as 4 camadas internas (mapa estático → slug direto → catálogo dinâmico → API Tesouro Nacional)

**Backend — `tesouro_nacional.py`**
- Headers anti-403 adicionados (`User-Agent`, `Accept`, `Referer`)
- Fallback adicional para endpoint `tesourotransparente.tesouro.gov.br` quando a API primária falha

**Backend — `rentabilidade_service.py`**
- `_proventos_total`: corrigido para usar `Dividend.total_value` (campo correto do modelo) em vez de `Dividend.amount`

**Backend — serviços de cotação**
- `quotes_service.py`: passa a usar `fetch_treasury_prices` com as 3 camadas de resolução de slug para Tesouro Direto
- `_normalize_crypto_ticker`: adicionado mapa `_CRYPTO_NAME_MAP` cobrindo 35 criptomoedas por nome completo (ex: `BITCOIN → BTC`, `CARDANO → ADA`)

### Adicionado — Página de Rentabilidade (25/06/2026)

**Backend**
- `rentabilidade_service.py`: serviço de agregação com 3 funções (`get_kpis`, `get_rentabilidade_por_ativo`, `get_rentabilidade_por_classe`), cache Redis TTL 5min, degradação gracosa sem Redis
- `routers/rentabilidade.py`: 3 endpoints REST com verificação de ownership por carteira:
  - `GET /api/v1/portfolios/{id}/rentabilidade/kpis` — 13 campos: patrimônio, custo, aportado, ganhos realizados/não-realizados, retorno total/mês/12m/desde início, proventos total e 12m
  - `GET /api/v1/portfolios/{id}/rentabilidade/ativos` — por ativo: qty, avg_price, current_value, unrealized/realized/total PnL, is_open
  - `GET /api/v1/portfolios/{id}/rentabilidade/classes` — agrupado por ACAO/FII/ETF com alocacao_pct e total_pnl_pct
- `main.py`: import e registro do `rentabilidade.router` na seção core financeiro
- `main.py`: fix typo `str(url)` → `str(request.url)` no `global_exception_handler`

**Testes**
- `test_rentabilidade_service.py`: 13 casos de teste com SQLite in-memory, mocks para cache e cotações:
  - `TestGetKpis` (5): sem snapshot, com snapshot, retorno 30d, fallback sem snap 30d, campos obrigatórios
  - `TestGetRentabilidadePorAtivo` (5): sem posições, aberta com cotação, sem cotação (fallback avg_price), zerada com realized, zerada sem realized (ignorada)
  - `TestGetRentabilidadePorClasse` (3): sem posições, agrupamento por tipo, alocacao_pct soma 100%

**Frontend**
- `rentabilidadeService.ts`: tipos TypeScript (`RentabilidadeKpis`, `RentabilidadeAtivo`, `RentabilidadeClasse`) + 3 métodos de API
- `useRentabilidade.ts`: hooks `useRentabilidadeKpis`, `useRentabilidadeAtivos`, `useRentabilidadeClasses` com React Query
- `RentabilidadePage.tsx`: página completa em `/carteira/rentabilidade`:
  - **8 KpiCards em 2 linhas** com subValues e indicadores de variação coloridos
  - **Coluna lateral** — Por classe: barra de alocação visual + retorno colorido por tipo
  - **Tabela por ativo** — Qtd · P.M. · Val. atual · Ganho n.r. · Ganho real. · Total com filtro de tipo e toggle de posições zeradas
  - Skeletons de carregamento, estados vazios, link discreto para posições zeradas
  - Seletor de carteira quando há múltiplas carteiras
  - Data do último snapshot no cabeçalho

### Adicionado (anterior)
- `asset_seed_service.py`: serviço que popula a tabela `assets` via BRAPI `/quote/list` com UPSERT por `(ticker, asset_type)` para Ações, FIIs, ETFs Nacionais e BDRs
- `POST /api/v1/admin/assets/seed`: endpoint restrito a superadmin que dispara o seed em background e retorna `202 Accepted`
- Job semanal automático `job_seed_assets` toda segunda-feira às 03h no scheduler
- Backfill histórico de preços com **ordenação por prioridade de tipo**: ACAO → FII → ETF_NACIONAL → ETF_INTERNACIONAL → STOCK → BDR → outros, evitando rate-limit prematuro do yfinance
- Aba **BDR** no modal de transações do frontend (`assetType: 'BDR'`, moeda BRL, ícone Globe2, autocomplete via BRAPI)
- Log detalhado com separadores visíveis (`==========`) no background task do seed para diagnóstico
- Traceback completo em caso de falha no seed via `traceback.format_exc()`

### Corrigido (anterior)
- `main.py`: removida Etapa 3 (backfill de proventos) da sequência de boot — proventos são triggerados corretamente por transação via `dividend_backfill_service`, não precisam de boot
- `price_history_backfill_service.py`: adicionada função `_sort_key` com `_TYPE_PRIORITY` para ordenar ativos no backfill inicial; BDRs (maioria sem histórico BRAPI) ficam por último
- `asset_onboarding_service.py`: removido import inexistente `upsert_daily_prices` de `price_history_service`; substituído por função local `_upsert_price_row` usando `pg_insert` diretamente
- `admin.py`: background task do seed agora loga início da execução antes de qualquer operação, evitando falhas silenciosas

---

## [0.15.0] — 2026-06-15

### Adicionado
- Módulo de metas financeiras (`goals`): CRUD completo com progresso calculado automaticamente
- Módulo IRPF: cálculo de imposto sobre ganho de capital por operações de renda variável
- Módulo de análise de carteira (`analysis`): score de diversificação, concentração por setor e sugestões
- Módulo de renda fixa (`fixed_income`): cadastro e acompanhamento de CDB, LCI, LCA, Debentures
- Módulo de cotações em tempo real (`quotes`): endpoint consolidado com cache Redis (TTL 15min)
- Módulo de preços históricos (`prices`): histórico OHLCV com fallback BRAPI → Alpha Vantage → yfinance
- Módulo Tesouro Direto (`treasury`): cadastro de títulos com cotação via BRAPI v2
- Módulo de câmbio (`fx`): cotação e histórico de pares cambiais via BRAPI v2/currency
- Módulo de class targets (`class_targets`): definição de alocação alvo por classe de ativo por carteira
- Scheduler APScheduler com 7 jobs: atualização de preços, proventos, câmbio, seed de ativos
- Rate limiter global via SlowAPI + middleware
- Cache Redis com TTL configurável por endpoint
- Integração Alpha Vantage com rate limiter dedicado (4 req/min via TokenBucket)
- Health check real com verificação de conectividade PostgreSQL e Redis
- Suporte a ativos internacionais (BDR, ETF_INTL, STOCK_INTL) via yfinance + Alpha Vantage

### Alterado
- Autenticação migrada para JWT com refresh token rotativo
- Senhas com bcrypt v5 (rounds configurável)
- Modelos de banco com soft-delete e timestamps automáticos

### Corrigido
- `price_history_service`: race condition em upsert de preços paralelos
- `dividend_backfill_service`: duplicatas em re-execução corrigidas com `ON CONFLICT DO NOTHING`

---

## [0.10.0] — 2026-05-01

### Adicionado
- Estrutura base do projeto: FastAPI + SQLAlchemy async + Alembic + PostgreSQL + Redis
- Docker Compose com serviços: backend, postgres, redis, nginx
- Módulos core: auth, users, portfolios, transactions, positions, dividends, proventos, performance
- Seed automático do superadmin no entrypoint
- Configuração de CORS, middleware de logging, handler global de exceções
- Integração BRAPI: cotações, histórico de preços, dados de ativos, Tesouro Direto
- Integração yfinance: fallback para ativos internacionais
- Modelo `Asset` com campos: ticker, name, asset_type, sector, currency, logo_url, last_price
- Modelo `AssetPrice` com constraint única `uq_price_asset_timestamp`
- Modelo `AssetDividend` para histórico de proventos
- Migrations Alembic versionadas

---

## [0.1.0] — 2026-04-01

### Adicionado
- Repositório criado, estrutura de pastas definida
- README e documentação inicial
- Decisão de arquitetura: monorepo com `backend/` e `frontend/`
