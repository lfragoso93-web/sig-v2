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

## 🔄 Sprint 5 — Frontend Dashboard (Em andamento)
**Período:** Junho–Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

### Concluído
- [x] **Página de Rentabilidade** (`/carteira/rentabilidade`) — 25/06/2026
- [x] **Hotfixes Tesouro Direto & Cripto** — 25/06/2026
- [x] **Fixes CSS/UI Design System** — 25/06/2026
- [x] **Dashboard principal** (`ResumePage`) — 26/06/2026
- [x] **Gráfico de rentabilidade mensal + benchmark** (`RentabilidadeChart`) — 26/06/2026
- [x] **Correção do Bug 3 — Evolução Patrimonial vazia** — 26/06/2026
- [x] **Fix rentabilidade renda fixa** — 28/06/2026
- [x] **Fix modal de lançamento — renda fixa sem cotas** — 28/06/2026
- [x] **Bump dependências frontend e backend** — 29/06/2026
- [x] **PR #78 criada** — `stable-15jun` → `main` — 29/06/2026

### Pendente
- [ ] `GET /api/v1/assets`: listagem paginada com filtros
- [ ] Tela de listagem de ativos no frontend

---

## 🔄 Sprint 5A — Botão + Lançamento no Mobile (Concluído — 26/06/2026)
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [x] `BottomNav` adicionado ao `AppLayout`
- [x] FAB 52×52px com elevação visual acima da barra
- [x] Área de toque mínima 44×44px em todos os itens (WCAG 2.5.8)
- [x] `aria-label` em todos os `NavLink` + `nav` + FAB

---

## 🔄 Sprint 5B — Performance de Queries + Rentabilidade
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

> **Criticidade: Alta | Esforço: Alto | Impacto: Performance + Precisão financeira**

- [ ] Mapear queries com tempo de execução elevado (EXPLAIN ANALYZE)
- [ ] Adicionar índices faltantes e otimizar joins
- [ ] Revisar N+1 em listagens de posições e transações
- [ ] Testes de integração do fluxo de proventos
- [ ] **[NOVO]** Auditar e corrigir cálculo de rentabilidade diária (verificar base de comparação)
- [ ] **[NOVO]** Auditar e corrigir cálculo de rentabilidade mensal (TWR vs MWRR)
- [ ] **[NOVO]** Validar rentabilidade total acumulada contra cálculo manual de referência
- [ ] **[NOVO]** Criar conjunto de dados de teste determinístico para validar os três horizontes

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

## 🔄 Sprint 5E — Distribuição Ideal da Carteira (BDR + Resumo) [NOVO]
**Período:** Julho 2026 | [Issue #60](https://github.com/lfragoso93-web/sig-v2/issues/60)

> **Criticidade: Alta | Esforço: Baixo-Médio | Impacto: Funcionalidade core**

- [ ] Incluir classe `BDR` no módulo `class_targets` (backend)
- [ ] Garantir que BDRs apareçam no cálculo de alocação atual vs. alvo
- [ ] Exibir barra de distribuição alvo na `ResumePage` (Dashboard)
- [ ] Indicar desvio entre alocação real e alvo por classe (delta colorido)
- [ ] Endpoint atualizado para retornar `class_targets` incluindo BDR

---

## 📋 Sprint 6 — Qualidade Visual & Rename SGI (Planejado)
**Período:** Julho–Agosto 2026 | [Issue #55](https://github.com/lfragoso93-web/sig-v2/issues/55)

### Sprint 6A — Análise de Impacto: Rename SIG v2 → SGI + Remoção de Referências a APIs Externas [NOVO]

> **Criticidade: Alta | Esforço: Baixo | Impacto: Segurança / Compliance**

- [ ] Inventariar todas as ocorrências de `SIG` no código, docs, CI e banco
- [ ] Verificar nomes de variáveis, tabelas, logs e env vars
- [ ] Verificar badges e links externos
- [ ] **[NOVO]** Remover todas as menções explícitas a nomes de APIs externas em documentação pública (README, CHANGELOG, ROADMAP, Swagger)
- [ ] **[NOVO]** Substituir referências por termos genéricos: "provedor de cotações", "serviço de câmbio", "fonte de dados externos"
- [ ] **[NOVO]** Manter nomes técnicos apenas em `.env.example` com comentários de propósito, sem revelar fornecedor
- [ ] **[NOVO]** Revisar Swagger/OpenAPI: remover nomes de provedores em descrições de endpoints
- [ ] Propor plano de migração seguro do rename
- [ ] Só então aplicar o rename em commit único e documentado

### Sprint 6B — Aprimorar UI Global + Patrimônio Analítico [NOVO]

> **Patrimônio — Criticidade: Média | Esforço: Médio | Impacto: UX / diferenciação visual**

- [ ] Revisar bordas cortando conteúdo (tabelas, cards, modais)
- [ ] Padronizar espaçamento e tipografia entre páginas
- [ ] Melhorar responsividade geral (tablet e mobile)
- [ ] Revisitar `Transacoes.tsx` — interface mais leve e moderna
- [ ] **[NOVO] Reformular `PatrimonioPage.tsx`** — transformar em página analítica distinta de Rentabilidade:
  - [ ] Visão de composição: % de cada ativo dentro de sua classe (treemap ou barras empilhadas)
  - [ ] Métricas por ativo: peso, valor investido, valor atual, variação absoluta e relativa
  - [ ] Concentração de risco: top 5 ativos como % do patrimônio total
  - [ ] Comparativo alocação real vs. alvo (`class_targets`) com indicação visual de desvio
  - [ ] Evolução da composição ao longo do tempo (gráfico de área empilhada)
  - [ ] Tabela colapsável por classe com drill-down por ativo
  - [ ] Remover redundâncias com `RentabilidadePage` (evitar duplicar KPIs de retorno)
  - [ ] Sugestões adicionais de melhoria:
    - [ ] Indicador de diversificação (score já existe no backend via `analysis`)
    - [ ] Alertas de concentração excessiva (>30% em um ativo)
    - [ ] Linha do tempo de evolução do patrimônio por classe
    - [ ] Painel de "próximo aporte sugerido" com base no desvio da alocação alvo

### Sprint 6C — Limpeza de Rotas e Arquivos Legados
- [ ] Padronizar todas as rotas para `/carteira/*`
- [ ] Remover rota duplicada `/patrimonio`
- [ ] Remover redirects legados desnecessários
- [ ] Deletar arquivos stub/fantasma: `Proventos.tsx`, `Rentabilidade.tsx`, `Resumo.tsx`
- [ ] Atualizar `App.tsx` após limpeza e validar todas as rotas

### Sprint 6D — Import de Ativos via CSV [NOVO]

> **Criticidade: Alta | Esforço: Médio | Impacto: UX / Onboarding**

- [ ] Definir schema do CSV modelo (ticker, tipo, quantidade, preço médio, data)
- [ ] Endpoint `GET /api/v1/assets/csv-template` — retorna CSV modelo para download
- [ ] Endpoint `POST /api/v1/portfolios/{id}/import-csv` — valida e importa ativos em massa
- [ ] Validação linha a linha com relatório de erros por linha
- [ ] Transação atômica: importação total ou rollback completo
- [ ] Frontend: botão "Importar via CSV" na tela de transações ou patrimônio
- [ ] Modal com preview das linhas antes de confirmar
- [ ] Download do modelo CSV diretamente no modal de importação
- [ ] Suporte a ativos nacionais (ACAO, FII, BDR) e internacionais (STOCK_INTL, ETF_INTL)

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

### Sprint 7B — Logs de Auditoria por Usuário _(movido da Sprint 5C)_

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

### Sprint 10B — Backup e Restore do Banco via Sistema [NOVO]

> **Criticidade: Alta | Esforço: Médio-Alto | Impacto: Resiliência / Disaster Recovery**

- [ ] Endpoint `POST /api/v1/admin/database/backup` — gera dump PostgreSQL e retorna arquivo para download (superadmin)
- [ ] Endpoint `POST /api/v1/admin/database/restore` — recebe arquivo de backup e restaura (superadmin)
- [ ] Autenticação dupla: confirmação por senha antes de executar restore
- [ ] Backup armazenado temporariamente em volume Docker com TTL de 24h
- [ ] Log de todas as operações de backup/restore em `AuditLog`
- [ ] Frontend: painel de administração com botões de backup e restore
- [ ] Aviso de impacto: modal de confirmação com alerta de downtime esperado
- [ ] Testes de integração: backup → restore → verificar integridade dos dados

---

## 🗂 Backlog (Sem sprint definida)

- [ ] Notificações por e-mail (proventos recebidos, metas atingidas)
- [ ] Importação de notas de corretagem (PDF parsing)
- [ ] Simulador de aportes
- [ ] App mobile (React Native)
- [ ] Multi-tenancy (múltiplos usuários com isolamento completo)
