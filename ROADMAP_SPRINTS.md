# Roadmap de Sprints — SGI v2

> Última atualização: 30/06/2026
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
- [x] Integração de dados de mercado base (cotações + histórico)

---

## ✅ Sprint 2 — Core Financeiro (Concluído)
**Período:** Maio 2026 | [Issue #51](https://github.com/lfragoso93-web/sig-v2/issues/51)

- [x] Módulo dividends e proventos com backfill histórico
- [x] Módulo performance (rentabilidade, TWR, benchmark)
- [x] Módulo fx (câmbio)
- [x] Módulo Tesouro Direto
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

- [x] `asset_seed_service`: popula tabela `assets` com UPSERT idempotente (2.259 ativos)
- [x] `POST /api/v1/admin/assets/seed`: endpoint superadmin com resposta `202 Accepted` + background task
- [x] Job semanal automático (toda segunda às 03h) para seed incremental de novos IPOs
- [x] Backfill histórico de preços com ordenação por tipo: ACAO/FII primeiro, BDR por último
- [x] Fix: boot sequence sem Etapa 3 redundante
- [x] Fix: `ImportError upsert_daily_prices` removido de `asset_onboarding_service`
- [x] Fix: background task do seed com log de início + traceback completo
- [x] Frontend: aba **BDR** adicionada no modal de transações

---

## ✅ Sprint 5 — Frontend Dashboard (Concluído — 30/06/2026)
**Período:** Junho–Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [x] **Página de Rentabilidade** (`/carteira/rentabilidade`) — 25/06/2026
- [x] **Hotfixes Tesouro Direto & Cripto** — 25/06/2026
- [x] **Fixes CSS/UI Design System** — 25/06/2026
- [x] **Dashboard principal** (`ResumePage`) — 26/06/2026
- [x] **Gráfico de rentabilidade mensal + benchmark** (`RentabilidadeChart`) — 26/06/2026
- [x] **Correção do Bug 3 — Evolução Patrimonial vazia** — 26/06/2026
- [x] **Fix rentabilidade renda fixa** — 28/06/2026
- [x] **Fix modal de lançamento — renda fixa sem cotas** — 28/06/2026
- [x] **Bump dependências frontend e backend** — 29/06/2026
- [x] **Fix rentabilidade dia/mês/12m + KpiCard Rentabilidade reestruturado** — 30/06/2026

---

## ✅ Sprint 5A — Botão + Lançamento no Mobile (Concluído — 26/06/2026)
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [x] `BottomNav` adicionado ao `AppLayout`
- [x] FAB 52×52px com elevação visual acima da barra
- [x] Área de toque mínima 44×44px em todos os itens (WCAG 2.5.8)
- [x] `aria-label` em todos os `NavLink` + `nav` + FAB

---

## ✅ Sprint 5E — Distribuição Ideal da Carteira: BDR + Reflexo no Resumo (Concluído — 30/06/2026)
**Período:** Julho 2026 | [Issue #79](https://github.com/lfragoso93-web/sig-v2/issues/79)

- [x] `BDR` adicionado a `VALID_ASSET_CLASSES` e `_TYPE_LABEL` no `class_target_service`
- [x] `get_targets_with_current()` retorna BDR quando há posição ou meta configurada
- [x] `AllocationTargetWidget` itera `rows` dinamicamente — BDR renderizado automaticamente
- [x] Widget exibido na `ResumePage` sob o gráfico de distribuição ("Alvo da Carteira")
- [x] `useClassTargets` já chamava `/targets-with-current` — nenhuma alteração necessária

---

## ✅ Sprint 5F — Sync Semanal de Dividendos de FIIs (Concluído — 30/06/2026)
**Período:** Julho 2026

> Pipeline completo de sincronização de proventos de FIIs via provedor de cotações. Job automático toda sábado às 6h BRT.

- [x] Configurações: `FII_DIVIDEND_CHUNK_SIZE`, `FII_DIVIDEND_MAX_RETRIES`, `FII_DIVIDEND_BOOTSTRAP_YEARS`
- [x] `integrations/brapi_fii_dividends.py`: client com retry exponencial (429/5xx), chunking e DTO `FiiDividendEvent`
- [x] `models/dividends_sync_job.py` + migration `012`: lock distribuído, cursor incremental, métricas por run
- [x] `services/dividends_sync_service.py`: orquestrador lock → fetch → upsert sem N+1 → release
- [x] `scheduler.py`: `job_sync_fii_dividends` — sábado 6h BRT — contador 7 → **8 jobs**
- [x] `routers/admin.py`: `GET /admin/fii-dividends/sync/status` e `POST /admin/fii-dividends/sync`

---

## ✅ Sprint 6B — PatrimonioPage Analítica + Bugfixes Críticos (Concluído — 30/06/2026)
**Período:** Junho 2026

> Reformulação completa da página Patrimônio com foco analítico, correção de 3 bugs críticos e limpeza de arquivos legados.

### Bugfixes
- [x] **Bug 1 — Backend**: Migration 022 cria `payment_date`, `ex_date`, `value_per_unit`, `total_received`, `dividend_type` na tabela `dividends` — resolve filtro `since` em `_proventos_total` — 30/06/2026
- [x] **Bug 2 — Frontend**: Guards `(Number(v) || 0)` em `formatPercent`/`formatBRL` e `safeNum` nos props `change` dos `KpiCard` — elimina crash `toFixed on undefined` — 30/06/2026
- [x] **Bug 3 — Backend**: `get_rentabilidade_por_ativo` e `get_rentabilidade_por_classe` adicionados ao `rentabilidade_service` — resolve `ImportError` que impedia o boot — 30/06/2026

### PatrimonioPage — Reformulação
- [x] Aba **Histórico** removida (duplicava `RentabilidadePage`)
- [x] **Visão Geral**: KPIs + evolução mensal (barras) + donut de alocação por classe + widget Distribuição Ideal vs. Atual + tabela de posições
- [x] **Aba Análise**: Score HHI (baixo/moderado/alto/crítico) + Top 5 posições + concentração por classe (donut + barras horizontais) + desvio do alvo
- [x] **Treemap SVG puro** com algoritmo Squarified — sem dependências externas
- [x] Toggle diário/mensal e seletor de período no gráfico de evolução

---

## ✅ Sprint 6C — Limpeza de Rotas e Arquivos Legados (Concluído — 30/06/2026)
**Período:** Junho 2026

- [x] `HistoricoPage.tsx` removido + rota `/carteira/historico` removida do router
- [x] `Login.tsx` e `Register.tsx` duplicados de `auth/` removidos
- [x] `Landing.tsx` restaurado com rota pública `/` em `main.tsx`
- [x] `App.tsx` mantido como legado sem re-export que quebrava o build

---

## 🔄 Sprint 5B — Performance de Queries (Em andamento)
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

> **Criticidade: Alta | Esforço: Alto | Impacto: Performance**

### Concluído
- [x] **Fix `retorno_dia_pct`**: usa `_snapshot_before_today()` — trata fins de semana e feriados corretamente — 30/06/2026
- [x] **Fix `retorno_mes_pct`**: usa 1º do mês calendário como base fixa (antes usava D-30 corridos) — 30/06/2026
- [x] **`retorno_dia_pct` adicionado ao tipo `RentabilidadeKpis`** no frontend — 30/06/2026
- [x] **KpiCard Rentabilidade** exibe Hoje / Mês / 12m / Desde o início com cores semânticas — 30/06/2026

### Pendente
- [ ] Mapear queries com tempo de execução elevado (EXPLAIN ANALYZE)
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

- [x] `ProventosHistoricoTable.tsx` — CSS vars corretos (validado)
- [x] `ProventosDonutChart.tsx` — PALETTE migrada para `--color-chart-2..10`
- [ ] Testes de integração do fluxo de proventos _(postergado para Sprint 5B)_

---

## 📋 Sprint 6 — Qualidade Visual & Rename SGI (Planejado)
**Período:** Julho–Agosto 2026 | [Issue #55](https://github.com/lfragoso93-web/sig-v2/issues/55)

### Sprint 6A — Remoção de Referências a APIs Externas

> **Criticidade: Alta | Esforço: Baixo | Impacto: Segurança / Compliance**

- [ ] Remover todas as menções explícitas a nomes de APIs externas em documentação pública
- [ ] Substituir referências por termos genéricos: "provedor de cotações", "serviço de câmbio"
- [ ] Manter nomes técnicos apenas em `.env.example` com comentários de propósito
- [ ] Revisar Swagger/OpenAPI: remover nomes de provedores em descrições de endpoints
- [ ] Análise de impacto para rename SIG v2 → SGI

### Sprint 6D — Import de Ativos via CSV

> **Criticidade: Alta | Esforço: Médio | Impacto: UX / Onboarding**

- [ ] Definir schema do CSV modelo (ticker, tipo, quantidade, preço médio, data)
- [ ] Endpoint `GET /api/v1/assets/csv-template` — retorna CSV modelo para download
- [ ] Endpoint `POST /api/v1/portfolios/{id}/import-csv` — valida e importa ativos em massa
- [ ] Validação linha a linha com relatório de erros por linha
- [ ] Transação atômica: importação total ou rollback completo
- [ ] Frontend: botão "Importar via CSV" na tela de transações ou patrimônio
- [ ] Modal com preview das linhas antes de confirmar
- [ ] Download do modelo CSV diretamente no modal de importação

---

## 📋 Sprint 7 — Módulo de IRPF (Planejado)
**Período:** Agosto 2026 | [Issue #56](https://github.com/lfragoso93-web/sig-v2/issues/56)

### Sprint 7A — Módulo IRPF
- [ ] Completar `IRPFPage.tsx`
- [ ] Exportação de relatório mensal/anual (PDF ou CSV)
- [ ] Cálculo consolidado por ano-calendário
- [ ] Isenção para vendas até R$20.000/mês
- [ ] Apuração Day Trade vs Swing Trade
- [ ] Testes de validação do cálculo de ganho de capital

### Sprint 7B — Logs de Auditoria por Usuário

> **Criticidade: Média | Esforço: Médio | Impacto: Governança interna**

- [ ] Criar modelo `AuditLog` (user_id, action, resource, timestamp, metadata)
- [ ] Middleware ou decorator para captura automática de escrita
- [ ] Endpoint `GET /admin/users/{id}/audit` para superadmin
- [ ] Tela de auditoria no painel admin (tabela com filtros por usuário, data, ação)
- [ ] Exportação de log em CSV pelo superadmin

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

### Sprint 10B — Backup e Restore do Banco via Sistema

> **Criticidade: Alta | Esforço: Médio-Alto | Impacto: Resiliência / Disaster Recovery**

- [ ] Endpoint `POST /api/v1/admin/database/backup` — dump PostgreSQL para download (superadmin)
- [ ] Endpoint `POST /api/v1/admin/database/restore` — recebe arquivo e restaura (superadmin)
- [ ] Autenticação dupla: confirmação por senha antes de executar restore
- [ ] Backup com TTL de 24h em volume Docker
- [ ] Log de todas as operações em `AuditLog`
- [ ] Frontend: painel de administração com botões de backup e restore
- [ ] Modal de confirmação com alerta de downtime
- [ ] Testes de integração: backup → restore → verificar integridade

---

## 🗂 Backlog (Sem sprint definida)

- [ ] Notificações por e-mail (proventos recebidos, metas atingidas)
- [ ] Importação de notas de corretagem (PDF parsing)
- [ ] Simulador de aportes
- [ ] App mobile (React Native)
- [ ] Multi-tenancy (múltiplos usuários com isolamento completo)
