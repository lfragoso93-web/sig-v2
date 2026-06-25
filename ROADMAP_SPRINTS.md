# Roadmap de Sprints — SGI v2

> Última atualização: 25/06/2026

---

## ✅ Sprint 1 — Fundação (Concluído)
**Período:** Abril 2026

- [x] Estrutura do projeto (FastAPI + SQLAlchemy async + Alembic)
- [x] Docker Compose (backend, postgres, redis, nginx)
- [x] Auth JWT com refresh token rotativo
- [x] Módulos: auth, users, portfolios, transactions, positions
- [x] Seed automático do superadmin
- [x] Health check real (PostgreSQL + Redis)
- [x] Integração BRAPI base (cotações + histórico)

---

## ✅ Sprint 2 — Core Financeiro (Concluído)
**Período:** Maio 2026

- [x] Módulo dividends e proventos com backfill histórico
- [x] Módulo performance (rentabilidade, TWR, benchmark)
- [x] Módulo fx (câmbio BRAPI v2)
- [x] Módulo Tesouro Direto
- [x] Integração Alpha Vantage com rate limiter
- [x] Suporte a ativos internacionais (BDR, ETF_INTL, STOCK_INTL)
- [x] Cache Redis (TTL 15min) nos endpoints de cotação
- [x] Scheduler APScheduler (atualização automática de preços e proventos)
- [x] Rate limiter global SlowAPI

---

## ✅ Sprint 3 — Funcionalidades Avançadas (Concluído)
**Período:** Junho 2026 (1ª quinzena)

- [x] Módulo goals (metas financeiras com progresso automático)
- [x] Módulo IRPF (ganho de capital renda variável)
- [x] Módulo analysis (score de diversificação, concentração por setor)
- [x] Módulo fixed_income (CDB, LCI, LCA, Debêntures)
- [x] Módulo quotes (cotações consolidadas em tempo real)
- [x] Módulo prices (histórico OHLCV com fallback em cascata)
- [x] Módulo class_targets (alocação alvo por carteira)
- [x] Asset onboarding service (histórico + proventos + logo no primeiro cadastro)

---

## ✅ Sprint 4 — Catálogo de Ativos e Dados (Concluído)
**Período:** Junho 2026 (2ª quinzena) — concluído em 24/06/2026

- [x] `asset_seed_service`: popula tabela `assets` via BRAPI `/quote/list` com UPSERT idempotente (2.259 ativos)
- [x] `POST /api/v1/admin/assets/seed`: endpoint superadmin com resposta `202 Accepted` + background task
- [x] Job semanal automático (toda segunda às 03h) para seed incremental de novos IPOs
- [x] Backfill histórico de preços com ordenação por tipo: ACAO/FII primeiro, BDR por último
- [x] Fix: boot sequence sem Etapa 3 redundante (proventos disparados por transação, não no boot)
- [x] Fix: `ImportError upsert_daily_prices` removido de `asset_onboarding_service`
- [x] Fix: background task do seed com log de início + traceback completo em caso de falha
- [x] Frontend: aba **BDR** adicionada no modal de transações (entre ETF BR e Stock)

---

## 🔄 Sprint 5 — Frontend Dashboard (Em andamento)
**Período:** Junho–Julho 2026

- [x] **Página de Rentabilidade** (`/carteira/rentabilidade`) — concluído em 25/06/2026
  - [x] Backend: `rentabilidade_service.py` com KPIs, por ativo e por classe (cache Redis TTL 5min)
  - [x] Backend: `routers/rentabilidade.py` com 3 endpoints + verificação de ownership
  - [x] Testes: `test_rentabilidade_service.py` com 13 casos (SQLite in-memory + mocks)
  - [x] Frontend: `rentabilidadeService.ts` + `useRentabilidade.ts` + `RentabilidadePage.tsx`
  - [x] UI: 8 KpiCards, barra por classe de ativo, tabela por ativo com filtros
- [x] **Hotfixes Tesouro Direto & Cripto** — concluído em 25/06/2026
  - [x] `fetch_treasury_indicators`: 3 camadas de fallback (BRAPI /indicators → /list → radaropcoes)
  - [x] `tesouro_nacional.py`: headers anti-403 + fallback tesourotransparente
  - [x] `rentabilidade_service._proventos_total`: campo `Dividend.total_value` corrigido
  - [x] `_normalize_crypto_ticker`: mapa de 35 nomes completos de criptomoedas (BITCOIN → BTC)
  - [x] `quotes_service`: passa a usar `fetch_treasury_prices` com 4 camadas de resolução
- [x] **Fixes CSS/UI Design System** — concluído em 25/06/2026
  - [x] `globals.css`: `.table-dense`, `.badge`, `.page-container/header/title`, `.input-xs`, `.text-muted`
  - [x] `components.css`: `.positions-table` com `table-layout: fixed` + larguras por coluna
  - [x] `Transacoes.tsx`: `page-container/header/title`, tooltip Recharts desbloqueado, `input-xs` correto
  - [x] `PatrimonioPage.tsx`: `<ToggleGroup>` com border-radius por botão, `table-dense` + ícones `TrendingUp/Down`
- [ ] Dashboard principal com resumo de patrimônio
- [ ] Gráfico de evolução patrimonial (linha histórica)
- [ ] Distribuição por classe de ativo (pizza/donut)
- [ ] Lista de posições com rentabilidade individual
- [ ] Tela de metas financeiras
- [ ] Tela IRPF (exportação de relatório)
- [ ] Tela de renda fixa
- [ ] `GET /api/v1/assets`: listagem paginada com filtros por tipo, setor e busca por nome/ticker
- [ ] `GET /api/v1/assets/{ticker}`: detalhe do ativo com cotação atual
- [ ] Tela de listagem de ativos no frontend
- [ ] Investigar e corrigir `YFRateLimitError` para ativos internacionais (IVV, NVDA, INTR, TFLO)

---

## 📋 Sprint 6 — Produção e Qualidade (Planejado)
**Período:** Agosto 2026

- [ ] Testes unitários e de integração (cobertura mínima 70%)
- [ ] CI/CD com GitHub Actions (lint + test + build)
- [ ] Deploy em ambiente de produção (VPS ou Railway)
- [ ] Monitoramento com Sentry ou similar
- [ ] Documentação da API (Swagger customizado)
- [ ] Backups automáticos do PostgreSQL

---

## 🗂 Backlog (Sem sprint definida)

- [ ] Notificações por e-mail (proventos recebidos, metas atingidas)
- [ ] Importação de notas de corretagem (PDF parsing)
- [ ] Comparação de carteira com benchmark (IBOV, CDI)
- [ ] Simulador de aportes
- [ ] App mobile (React Native)
- [ ] Multi-tenancy (múltiplos usuários com isolamento completo)
