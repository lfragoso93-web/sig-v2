# 🗺 Roadmap Visual — SGI v2

> Última atualização: 26/06/2026
> Acompanhe o progresso pelo [board de issues](https://github.com/lfragoso93-web/sig-v2/issues) com as labels `shipped`, `in-progress` e `planned`.

---

## Visão Geral

| Sprint | Entrega | Status | Issue |
|---|---|:---:|:---:|
| Sprint 1 | 🚀 Fundação | ✅ Shipped | [#50](https://github.com/lfragoso93-web/sig-v2/issues/50) |
| Sprint 2 | 💰 Core Financeiro | ✅ Shipped | [#51](https://github.com/lfragoso93-web/sig-v2/issues/51) |
| Sprint 3 | ⚙️ Funcionalidades Avançadas | ✅ Shipped | [#52](https://github.com/lfragoso93-web/sig-v2/issues/52) |
| Sprint 4 | 🗂 Catálogo de Ativos | ✅ Shipped | [#53](https://github.com/lfragoso93-web/sig-v2/issues/53) |
| Sprint 5 | 📊 Frontend Dashboard | 🔄 In Progress | [#54](https://github.com/lfragoso93-web/sig-v2/issues/54) |
| Sprint 5A | 📱 Botão + Lançamento no mobile | 📝 Planned | [#54](https://github.com/lfragoso93-web/sig-v2/issues/54) |
| Sprint 5B | ⚡ Performance de Queries | 📝 Planned | [#54](https://github.com/lfragoso93-web/sig-v2/issues/54) |
| Sprint 5C | 🔐 Logs de Auditoria por Usuário | 📝 Planned | [#54](https://github.com/lfragoso93-web/sig-v2/issues/54) |
| Sprint 5D | 💸 Proventos (fechar pendências) | 📝 Planned | [#54](https://github.com/lfragoso93-web/sig-v2/issues/54) |
| Sprint 6 | 🎨 Qualidade Visual & Rename SGI | 📝 Planned | [#55](https://github.com/lfragoso93-web/sig-v2/issues/55) |
| Sprint 7 | 🧾 Módulo de IRPF | 📝 Planned | [#56](https://github.com/lfragoso93-web/sig-v2/issues/56) |
| Sprint 8 | 📈 Análise de Carteira | 📝 Planned | [#57](https://github.com/lfragoso93-web/sig-v2/issues/57) |
| Sprint 9 | 🔍 Janela Global do Ativo | 📝 Planned | [#58](https://github.com/lfragoso93-web/sig-v2/issues/58) |
| Sprint 10 | 🚀 Produção e Qualidade | 📝 Planned | [#59](https://github.com/lfragoso93-web/sig-v2/issues/59) |

---

## 🏷 Labels de Status

| Label | Significado |
|---|---|
| `shipped` | Entrega concluída e estável |
| `in-progress` | Em desenvolvimento ativo |
| `planned` | Planejado, aguardando início |

Filtros rápidos:
- [✅ Shipped](https://github.com/lfragoso93-web/sig-v2/issues?q=label%3Ashipped)
- [🔄 In Progress](https://github.com/lfragoso93-web/sig-v2/issues?q=label%3Ain-progress)
- [📝 Planned](https://github.com/lfragoso93-web/sig-v2/issues?q=label%3Aplanned)

---

## ✅ Shipped (Concluído)

### [Sprint 1 — Fundação](https://github.com/lfragoso93-web/sig-v2/issues/50) · Abril 2026
Estrutura base: FastAPI async, Docker Compose, JWT auth, módulos core, seed do superadmin, health check real, BRAPI base.

### [Sprint 2 — Core Financeiro](https://github.com/lfragoso93-web/sig-v2/issues/51) · Maio 2026
Dividendos, performance, câmbio, Tesouro Direto, Alpha Vantage, ativos internacionais, cache Redis, scheduler, rate limiter.

### [Sprint 3 — Funcionalidades Avançadas](https://github.com/lfragoso93-web/sig-v2/issues/52) · Junho 2026 (1ª quinzena)
Metas, IRPF backend, análise, renda fixa, cotações, preços OHLCV, class targets, asset onboarding.

### [Sprint 4 — Catálogo de Ativos](https://github.com/lfragoso93-web/sig-v2/issues/53) · 24/06/2026
Seed de 2.259 ativos via BRAPI, job semanal, backfill priorizado por tipo, aba BDR no modal de transações.

---

## 🔄 In Progress

### [Sprint 5 — Frontend Dashboard](https://github.com/lfragoso93-web/sig-v2/issues/54) · Junho–Julho 2026

**Já entregue dentro da Sprint 5:**
- ✅ Página de Rentabilidade completa (8 KpiCards, tabela por ativo, filtros)
- ✅ Hotfixes Tesouro Direto (3 camadas de fallback) e Cripto (35 tickers normalizados)
- ✅ CSS Design System (`.table-dense`, `.badge`, `.page-container`, `.positions-table`)

**Ainda pendente:**
- Dashboard principal + gráfico de evolução patrimonial
- Distribuição por classe (pizza/donut), lista de posições com rentabilidade
- Telas de metas, renda fixa, IRPF (exportação)
- Listagem de ativos no frontend, fix `YFRateLimitError`

**Sub-sprints de bugs/melhorias (novos):**

#### 📱 Sprint 5A — Botão + Lançamento no mobile
Corrigir exibição e acesso ao botão de adição rápida em telas móveis.

#### ⚡ Sprint 5B — Performance de Queries
Mapear queries com tempo elevado, adicionar índices faltantes, revisar N+1 em listagens.

#### 🔐 Sprint 5C — Logs de Auditoria por Usuário
Modelo `AuditLog`, middleware de captura, endpoint admin, tela de auditoria.

#### 💸 Sprint 5D — Proventos (fechar pendências)
Migrar CSS legado de `ProventosHistoricoTable`, validar `ProventosDonutChart`, testes de integração.

---

## 📝 Planned

### [Sprint 6 — Qualidade Visual & Rename SGI](https://github.com/lfragoso93-web/sig-v2/issues/55) · Julho–Agosto 2026
**6A:** Análise de impacto completa do rename SIG v2 → SGI antes de qualquer alteração de código.
**6B:** Polimento visual global — bordas, espaçamento, responsividade, Transacoes.tsx.

### [Sprint 7 — Módulo de IRPF](https://github.com/lfragoso93-web/sig-v2/issues/56) · Agosto 2026
Exportação de relatório, cálculo por ano-calendário, isenção R$20k/mês, Day Trade vs Swing Trade.

### [Sprint 8 — Análise de Carteira](https://github.com/lfragoso93-web/sig-v2/issues/57) · Agosto–Setembro 2026
Score de diversificação, concentração por setor, comparação vs metas de alocação, sugestões de rebalanceamento.

### [Sprint 9 — Janela Global do Ativo](https://github.com/lfragoso93-web/sig-v2/issues/58) · Setembro 2026
Drawer com histórico de preços, proventos globais, DY calculado, disponível em todas as telas com ticker.

### [Sprint 10 — Produção e Qualidade](https://github.com/lfragoso93-web/sig-v2/issues/59) · Outubro 2026
Testes (70% cobertura), CI/CD, deploy, Sentry, Swagger, backup automático PostgreSQL.

---

## 🗂 Backlog (Sem sprint definida)

- [ ] Notificações por e-mail (proventos recebidos, metas atingidas)
- [ ] Importação de notas de corretagem (PDF parsing)
- [ ] Comparação de carteira com benchmark (IBOV, CDI)
- [ ] Simulador de aportes
- [ ] App mobile (React Native)
- [ ] Multi-tenancy (múltiplos usuários com isolamento completo)

---

> 💡 **Como usar:** clique em qualquer issue para ver os critérios de aceite, checklist de tarefas e discussão. Use os filtros de label para filtrar por status.
