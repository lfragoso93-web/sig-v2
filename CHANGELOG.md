# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Unreleased] — branch `stable-15jun`

### Adicionado
- `asset_seed_service.py`: serviço que popula a tabela `assets` via BRAPI `/quote/list` com UPSERT por `(ticker, asset_type)` para Ações, FIIs, ETFs Nacionais e BDRs
- `POST /api/v1/admin/assets/seed`: endpoint restrito a superadmin que dispara o seed em background e retorna `202 Accepted`
- Job semanal automático `job_seed_assets` toda segunda-feira às 03h no scheduler
- Backfill histórico de preços com **ordenação por prioridade de tipo**: ACAO → FII → ETF_NACIONAL → ETF_INTERNACIONAL → STOCK → BDR → outros, evitando rate-limit prematuro do yfinance
- Aba **BDR** no modal de transações do frontend (`assetType: 'BDR'`, moeda BRL, ícone Globe2, autocomplete via BRAPI)
- Log detalhado com separadores visíveis (`==========`) no background task do seed para diagnóstico
- Traceback completo em caso de falha no seed via `traceback.format_exc()`

### Corrigido
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
