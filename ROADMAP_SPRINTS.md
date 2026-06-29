# Roadmap de Sprints — SGI v2

> Última atualização: 29/06/2026
> Versão visual e interativa: [ROADMAP_VISUAL.md](./ROADMAP_VISUAL.md)

---

## ✅ Sprint 1 — Fundação (Concluído)
**Período:** Abril 2026 | [Issue #50](https://github.com/lfragoso93-web/sig-v2/issues/50)

- [x] Estrutura do projeto (FastAPI + SQLAlchemy async + Alembic)
- [x] Docker Compose (backend, postgres, redis, nginx)
- [x] Auth JWT com refresh token rotativo
- [x] Módulos: auth, users, portfolios, transactions, positions
- [x] Seed automático do superadmin
- [x] Health check real (PostgreSQL + Redis)
- [x] Integração BRAPI base (cotações + histórico)

---

## ✅ Sprint 2 — Core Financeiro (Concluído)
**Período:** Maio 2026 | [Issue #51](https://github.com/lfragoso93-web/sig-v2/issues/51)

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
**Período:** Junho 2026 (1ª quinzena) | [Issue #52](https://github.com/lfragoso93-web/sig-v2/issues/52)

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
**Período:** Junho 2026 (2ª quinzena) — concluído em 24/06/2026 | [Issue #53](https://github.com/lfragoso93-web/sig-v2/issues/53)

- [x] `asset_seed_service`: popula tabela `assets` via BRAPI `/quote/list` com UPSERT idempotente (2.259 ativos)
- [x] `POST /api/v1/admin/assets/seed`: endpoint superadmin com resposta `202 Accepted` + background task
- [x] Job semanal automático (toda segunda às 03h) para seed incremental de novos IPOs
- [x] Backfill histórico de preços com ordenação por tipo: ACAO/FII primeiro, BDR por último
- [x] Fix: boot sequence sem Etapa 3 redundante
- [x] Fix: `ImportError upsert_daily_prices` removido de `asset_onboarding_service`
- [x] Fix: background task do seed com log de início + traceback completo
- [x] Frontend: aba **BDR** adicionada no modal de transações

---

## 🔄 Sprint 5 — Frontend Dashboard (Em andamento)
**Período:** Junho–Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

### Concluído
- [x] **Página de Rentabilidade** (`/carteira/rentabilidade`) — 25/06/2026
- [x] **Hotfixes Tesouro Direto & Cripto** — 25/06/2026
- [x] **Fixes CSS/UI Design System** — 25/06/2026
- [x] **Dashboard principal** (`ResumePage`) — 26/06/2026
  - [x] KpiCards via `rentabilidade/kpis`
  - [x] Evolução patrimonial + distribuição + tabela de posições
- [x] **Gráfico de rentabilidade mensal + benchmark** (`RentabilidadeChart`) — 26/06/2026
- [x] **Correção do Bug 3 — Evolução Patrimonial vazia** — 26/06/2026
  - [x] Fallback on-the-fly quando não há snapshots
  - [x] Backfill automático em background ao acessar histórico
  - [x] Correção do filtro por classe com parse de enum `AssetType`
  - [x] Fallback via `Transaction.asset_type` quando `assets` não cobre o ticker
- [x] **Fix rentabilidade renda fixa** — 28/06/2026
  - [x] Normalização de `asset_type` corrigida (string → enum)
  - [x] Comparação de `OperationType` enum corrigida
  - [x] Sessão isolada para upsert de `fixed_income`
  - [x] Cache invalidado após upsert RF/TD
  - [x] Endpoint `flush_cache` exposto
  - [x] Migration 015: campo `daily_liquidity` em `fixed_income_investments`
- [x] **Fix modal de lançamento — renda fixa sem cotas** — 28/06/2026
  - [x] `RENDA_FIXA` exibe apenas "Valor Investido" (sem campo de cotas)
  - [x] Quantidade fixada em 1 automaticamente
  - [x] Labels e placeholders revisados
- [x] **Bump dependências frontend e backend** — 29/06/2026
  - [x] `vite` 8.1.0, `plugin-react` 6.0.3, `autoprefixer` 10.5.2, `postcss` 8.5.16
  - [x] `@tanstack/react-query` 5.101.2
  - [x] `fastapi` ≥ 0.138.1
- [x] **PR #78 criada** — `stable-15jun` → `main` — 29/06/2026

### Pendente
- [ ] `GET /api/v1/assets`: listagem paginada com filtros
- [ ] Tela de listagem de ativos no frontend
- [ ] Sprint 5B — Performance de queries + testes de integração proventos

---

## 🔄 Sprint 5A — Botão + Lançamento no Mobile (Concluído — 26/06/2026)
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [x] `BottomNav` adicionado ao `AppLayout`
- [x] `main` com `padding-bottom` dinâmico: `calc(60px + env(safe-area-inset-bottom))`
- [x] FAB 52×52px com elevação visual acima da barra
- [x] Área de toque mínima 44×44px em todos os itens (WCAG 2.5.8)
- [x] `aria-label` em todos os `NavLink` + `nav` + FAB

---

## 🔄 Sprint 5B — Performance de Queries
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [ ] Mapear queries com tempo de execução elevado
- [ ] Adicionar índices faltantes e otimizar joins
- [ ] Revisar N+1 em listagens de posições e transações
- [ ] Testes de integração do fluxo de proventos

---

## 🔄 Sprint 5C — Logs de Auditoria por Usuário
**Período:** Julho 2026 → Movido para Sprint 7 | [Issue #56](https://github.com/lfragoso93-web/sig-v2/issues/56)

- [ ] Criar modelo `AuditLog` (user_id, action, resource, timestamp, metadata)
- [ ] Middleware ou decorator para captura automática de escrita
- [ ] Endpoint `GET /admin/users/{id}/audit` para superadmin
- [ ] Tela de auditoria no painel admin

---

## 🔄 Sprint 5D — Proventos (Fechar Pendências)
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [x] `ProventosHistoricoTable.tsx` — já usava CSS vars corretamente (validado)
- [x] `ProventosDonutChart.tsx` — PALETTE migrada para `--color-chart-2..10`
- [x] `ProventosDonutChart` consome dados reais via `useProventosDistribuicao` (validado)
- [ ] Testes de integração do fluxo de proventos _(postergado para Sprint 5B)_

---

## 📋 Sprint 6 — Qualidade Visual & Rename SGI (Planejado)
**Período:** Julho–Agosto 2026 | [Issue #55](https://github.com/lfragoso93-web/sig-v2/issues/55)

### Sprint 6A — Análise de Impacto: Rename SIG v2 → SGI
- [ ] Inventariar todas as ocorrências de `SIG` no código, docs, CI e banco
- [ ] Verificar nomes de variáveis, tabelas, logs e env vars
- [ ] Verificar badges e links externos
- [ ] Propor plano de migração seguro
- [ ] Só então aplicar o rename em commit único e documentado

### Sprint 6B — Aprimorar UI Global
- [ ] Revisar bordas cortando conteúdo (tabelas, cards, modais)
- [ ] Padronizar espaçamento e tipografia entre páginas
- [ ] Melhorar responsividade geral (tablet e mobile)
- [ ] Revisitar `Transacoes.tsx` — interface mais leve e moderna

---

## 📋 Sprint 7 — Módulo de IRPF (Planejado)
**Período:** Agosto 2026 | [Issue #56](https://github.com/lfragoso93-web/sig-v2/issues/56)

- [ ] Completar `IRPFPage.tsx`
- [ ] Exportação de relatório mensal/anual (PDF ou CSV)
- [ ] Cálculo consolidado por ano-calendário
- [ ] Isenção para vendas até R$20.000/mês
- [ ] Apuração Day Trade vs Swing Trade
- [ ] Testes de validação do cálculo de ganho de capital

---

## 📋 Sprint 8 — Análise de Carteira (Planejado)
**Período:** Agosto–Setembro 2026 | [Issue #57](https://github.com/lfragoso93-web/sig-v2/issues/57)

- [ ] Completar `AnalisePage.tsx`
- [ ] Score de diversificação por setor e classe
- [ ] Concentração por ativo com alertas de over-allocation
- [ ] Comparação vs. metas de alocação (`class_targets`)
- [ ] Sugestões de rebalanceamento

---

## 📋 Sprint 9 — Janela Global do Ativo (Planejado)
**Período:** Setembro 2026 | [Issue #58](https://github.com/lfragoso93-web/sig-v2/issues/58)

- [ ] Componente `AssetDetailDrawer.tsx`
- [ ] Gráfico de preço histórico (OHLCV)
- [ ] Histórico de proventos do ativo
- [ ] Dividend Yield (DY) calculado
- [ ] Disponível em PatrimonioPage, Transacoes e RentabilidadePage

---

## 📋 Sprint 10 — Produção e Qualidade (Planejado)
**Período:** Outubro 2026 | [Issue #59](https://github.com/lfragoso93-web/sig-v2/issues/59)

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
- [ ] Simulador de aportes
- [ ] App mobile (React Native)
- [ ] Multi-tenancy (múltiplos usuários com isolamento completo)
