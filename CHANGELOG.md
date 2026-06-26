# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Unreleased] — branch `stable-15jun`

### Corrigido — Evolução Patrimonial / Bug 3 (26/06/2026)

**`backend/app/routers/portfolios.py`**
- Endpoint `GET /portfolios/{portfolio_id}/patrimonio-history` agora detecta ausência de snapshots e dispara `backfill_snapshots` em background
- Adicionado fallback on-the-fly para retornar a série histórica imediatamente, sem depender do backfill terminar
- Agregação de todas as classes no modo `Todas as classes` quando a base histórica ainda não existe

**`backend/app/services/portfolio_class_evolution_service.py`**
- Corrigida comparação de `asset_type` com conversão explícita string → enum `AssetType`
- Adicionado fallback por `Transaction.asset_type` quando o join com `assets` não encontra ticker correspondente
- Melhorado tratamento para classe inválida com log explícito

**`backend/app/services/portfolio_snapshot_service.py`**
- Mantido fluxo de snapshots mensais como fonte principal do modo consolidado
- Backfill admin/manual continua disponível para popular a base histórica completa

---

### Adicionado — Dashboard Principal e Rentabilidade (26/06/2026)

**`frontend/src/pages/ResumePage.tsx`**
- KpiCards migrados de `usePortfolioSummary` para `useRentabilidadeKpis`
- 4 cards: Patrimônio Total, Resultado Total, Proventos 12m e Rentabilidade
- Removidos `QuickNav` e seletor de carteira inline
- Página enxuta: KPIs + evolução patrimonial + distribuição + tabela de posições

**`frontend/src/components/charts/RentabilidadeChart.tsx`**
- Gráfico de rentabilidade % mês a mês com benchmark
- Barras da carteira + linhas de IBOV, CDI e IPCA
- Filtro de período e toggles independentes

**`frontend/src/pages/RentabilidadePage.tsx`**
- `RentabilidadeChart` integrado entre KPIs e tabela de ativos

---

### Corrigido — CSS/UI Design System (25/06/2026)

**`frontend/src/styles/globals.css`**
- Adicionadas classes `.table-dense`, `.badge`, `.badge-primary`, `.page-container`, `.page-header`, `.page-title`, `.page-subtitle`, `.input-xs`, `.text-muted`

**`frontend/src/styles/components.css`**
- `.positions-table` com `table-layout: fixed`
- Overflow e ellipsis em colunas longas

**`frontend/src/pages/Transacoes.tsx`**
- Padronização de layout com tokens globais
- Ajustes em tooltip e inputs compactos

**`frontend/src/pages/PatrimonioPage.tsx`**
- Extraído componente genérico `ToggleGroup`
- Removido `overflow-hidden` onde cortava tooltip e estados ativos
- Tabela mensal migrada para `.table-dense`

---

### Corrigido — Tesouro Direto & Cripto (25/06/2026)

**Backend — `brapi.py`**
- Adicionada 3ª camada de fallback para Tesouro Direto
- Token inválido agora cai corretamente em fallback sem quebrar o fluxo

**Backend — `tesouro_nacional.py`**
- Headers anti-403 e fallback adicional para endpoint oficial

**Backend — `rentabilidade_service.py`**
- `_proventos_total` corrigido para usar `Dividend.total_value`

**Backend — serviços de cotação**
- `quotes_service.py`: resolução robusta de slugs do Tesouro
- `_normalize_crypto_ticker`: mapa ampliado para nomes completos de cripto

### Adicionado — Página de Rentabilidade (25/06/2026)

**Backend**
- `rentabilidade_service.py`: KPIs, visão por ativo e por classe, com cache Redis TTL 5min
- `routers/rentabilidade.py`: 3 endpoints REST
- `test_rentabilidade_service.py`: 13 casos de teste

**Frontend**
- `rentabilidadeService.ts` + `useRentabilidade.ts` + `RentabilidadePage.tsx`
- UI com 8 KPIs, barra por classe e tabela por ativo

### Adicionado (anterior)
- `asset_seed_service.py`: popula tabela `assets` via BRAPI com UPSERT
- `POST /api/v1/admin/assets/seed`: endpoint superadmin + background task
- Job semanal automático para seed incremental
- Backfill histórico de preços com ordenação por prioridade de tipo
- Aba **BDR** no modal de transações do frontend
- Endpoints/admin de backfill de snapshots para recuperação da base histórica

### Corrigido (anterior)
- Boot sequence sem Etapa 3 redundante de proventos
- `ImportError upsert_daily_prices` removido de `asset_onboarding_service`
- Background task do seed com log de início + traceback completo

---

## [0.15.0] — 2026-06-15

### Adicionado
- Módulo de metas financeiras (`goals`)
- Módulo IRPF
- Módulo de análise de carteira (`analysis`)
- Módulo de renda fixa (`fixed_income`)
- Módulo de cotações em tempo real (`quotes`)
- Módulo de preços históricos (`prices`)
- Módulo Tesouro Direto (`treasury`)
- Módulo de câmbio (`fx`)
- Módulo de class targets (`class_targets`)
- Scheduler APScheduler com 7 jobs
- Rate limiter global via SlowAPI
- Cache Redis com TTL configurável por endpoint
- Integração Alpha Vantage com rate limiter dedicado
- Health check real com PostgreSQL e Redis
- Suporte a ativos internacionais

### Alterado
- Autenticação migrada para JWT com refresh token rotativo
- Senhas com bcrypt v5
- Modelos de banco com soft-delete e timestamps automáticos

### Corrigido
- `price_history_service`: race condition em upsert paralelo
- `dividend_backfill_service`: duplicatas em re-execução

---

## [0.10.0] — 2026-05-01

### Adicionado
- Estrutura base do projeto: FastAPI + SQLAlchemy async + Alembic + PostgreSQL + Redis
- Docker Compose com backend, postgres, redis, nginx
- Módulos core: auth, users, portfolios, transactions, positions, dividends, proventos, performance
- Seed automático do superadmin no entrypoint
- Configuração de CORS, middleware de logging, handler global de exceções
- Integração BRAPI: cotações, histórico, dados de ativos, Tesouro Direto
- Integração yfinance: fallback para ativos internacionais
- Modelo `Asset`
- Modelo `AssetPrice`
- Modelo `AssetDividend`
- Migrations Alembic versionadas

---

## [0.1.0] — 2026-04-01

### Adicionado
- Repositório criado, estrutura de pastas definida
- README e documentação inicial
- Decisão de arquitetura: monorepo com `backend/` e `frontend/`
