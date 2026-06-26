# Roadmap de Sprints — SGI v2

> Última atualização: 26/06/2026
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
- [x] Fix: boot sequence sem Etapa 3 redundante (proventos disparados por transação, não no boot)
- [x] Fix: `ImportError upsert_daily_prices` removido de `asset_onboarding_service`
- [x] Fix: background task do seed com log de início + traceback completo em caso de falha
- [x] Frontend: aba **BDR** adicionada no modal de transações (entre ETF BR e Stock)

---

## 🔄 Sprint 5 — Frontend Dashboard (Em andamento)
**Período:** Junho–Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

### Concluído
- [x] **Página de Rentabilidade** (`/carteira/rentabilidade`) — 25/06/2026
  - [x] Backend: `rentabilidade_service.py` com KPIs, por ativo e por classe (cache Redis TTL 5min)
  - [x] Backend: `routers/rentabilidade.py` com 3 endpoints + verificação de ownership
  - [x] Testes: `test_rentabilidade_service.py` com 13 casos (SQLite in-memory + mocks)
  - [x] Frontend: `rentabilidadeService.ts` + `useRentabilidade.ts` + `RentabilidadePage.tsx`
  - [x] UI: 8 KpiCards, barra por classe de ativo, tabela por ativo com filtros
- [x] **Hotfixes Tesouro Direto & Cripto** — 25/06/2026
- [x] **Fixes CSS/UI Design System** — 25/06/2026
- [x] **Dashboard principal** (`ResumePage`) — 26/06/2026
  - [x] KpiCards migrados para `rentabilidade/kpis` (consistentes com RentabilidadePage)
  - [x] 4 cards: Patrimônio Total, Resultado Total, Proventos 12m, Rentabilidade
  - [x] Gráfico de evolução patrimonial + distribuição por classe + tabela de posições
  - [x] Página enxuta — sem redundâncias com a página de Rentabilidade
- [x] **Gráfico de rentabilidade mensal + benchmark** (`RentabilidadeChart`) — 26/06/2026
  - [x] Barras: retorno % mês a mês via `useMonthlyEvolution`
  - [x] Linhas: IBOV (BRAPI), CDI (BCB série 4391), IPCA (BCB série 433)
  - [x] Toggles independentes por benchmark, filtro de período (6m/12m/24m/todo)
  - [x] Integrado na `RentabilidadePage`

### Pendente
- [ ] Tela de metas financeiras
- [ ] Tela IRPF (exportação de relatório)
- [ ] Tela de renda fixa
- [ ] `GET /api/v1/assets`: listagem paginada com filtros
- [ ] Tela de listagem de ativos no frontend
- [ ] Fix `YFRateLimitError` para ativos internacionais (IVV, NVDA, INTR, TFLO)

---

## 🔄 Sprint 5A — Botão + Lançamento no Mobile
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [ ] Corrigir exibição do botão de adição rápida em telas móveis
- [ ] Garantir acessibilidade e tamanho de toque adequado

---

## 🔄 Sprint 5B — Performance de Queries
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [ ] Mapear queries com tempo de execução elevado
- [ ] Adicionar índices faltantes e otimizar joins
- [ ] Revisar N+1 em listagens de posições e transações

---

## 🔄 Sprint 5C — Logs de Auditoria por Usuário
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [ ] Criar modelo `AuditLog` (user_id, action, resource, timestamp, metadata)
- [ ] Middleware ou decorator para captura automática de escrita
- [ ] Endpoint `GET /admin/users/{id}/audit` para superadmin
- [ ] Tela de auditoria no painel admin

---

## 🔄 Sprint 5D — Proventos (Fechar Pendências)
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [ ] Migrar `ProventosHistoricoTable.tsx` para CSS vars
- [ ] Validar `ProventosDonutChart` com dados reais
- [ ] Testes de integração do fluxo de proventos

---

## 📋 Sprint 6 — Qualidade Visual & Rename SGI (Planejado)
**Período:** Julho–Agosto 2026 | [Issue #55](https://github.com/lfragoso93-web/sig-v2/issues/55)

### Sprint 6A — Análise de Impacto: Rename SIG v2 → SGI
- [ ] Inventariar todas as ocorrências de `SIG` no código, docs, CI e banco
- [ ] Verificar nomes de variáveis, tabelas, logs e env vars
- [ ] Verificar badges e links externos
- [ ] Propor plano de migração seguro
- [ ] **Só então aplicar** o rename em commit único e bem documentado

### Sprint 6B — Aprimorar UI Global
- [ ] Revisar bordas cortando conteúdo (tabelas, cards, modais)
- [ ] Padronizar espaçamento e tipografia entre todas as páginas
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
