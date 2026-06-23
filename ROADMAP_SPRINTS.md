# Roadmap de Sprints — SGI v2

> Última atualização: 23/06/2026

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

## 🔄 Sprint 4 — Catálogo de Ativos e Dados (Em andamento)
**Período:** Junho 2026 (2ª quinzena) — iniciado em 23/06/2026

### Concluído hoje (23/06/2026)
- [x] `asset_seed_service`: popula tabela `assets` via BRAPI `/quote/list` com UPSERT idempotente
- [x] `POST /api/v1/admin/assets/seed`: endpoint superadmin com resposta `202 Accepted` + background task
- [x] Job semanal automático (toda segunda às 03h) para seed incremental de novos IPOs
- [x] Fix: `ImportError upsert_daily_prices` removido de `asset_onboarding_service`
- [x] Fix: background task do seed com log de início + traceback completo em caso de falha

### Pendente (próxima sessão — 24/06/2026)
- [ ] Validar log do seed após rebuild (`[seed_bg] INICIANDO SEED DE ATIVOS`)
- [ ] Verificar contadores finais: `created`, `updated`, `skipped`, `errors`
- [ ] Investigar e corrigir `YFRateLimitError` para ativos internacionais (IVV, NVDA, INTR, TFLO)
  - Estratégia: TTL de cache para evitar re-tentativas a cada request
  - Ou: pré-popular via Alpha Vantage no primeiro acesso
- [ ] `GET /api/v1/assets`: listagem paginada com filtros por tipo, setor e busca por nome/ticker
- [ ] `GET /api/v1/assets/{ticker}`: detalhe do ativo com cotação atual
- [ ] Tela de listagem de ativos no frontend

---

## 📋 Sprint 5 — Frontend Dashboard (Planejado)
**Período:** Julho 2026

- [ ] Dashboard principal com resumo de patrimônio
- [ ] Gráfico de evolução patrimonial (linha histórica)
- [ ] Distribuição por classe de ativo (pizza/donut)
- [ ] Lista de posições com rentabilidade individual
- [ ] Tela de metas financeiras
- [ ] Tela IRPF (exportação de relatório)
- [ ] Tela de renda fixa

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
