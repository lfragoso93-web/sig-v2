# Roadmap de Sprints — SGI v2

> Última atualização: 04/07/2026
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
- [x] Cache Redis nos endpoints de cotação
- [x] Scheduler APScheduler
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

- [x] `asset_seed_service`: popula tabela `assets` com UPSERT idempotente
- [x] `POST /api/v1/admin/assets/seed`: endpoint superadmin com background task
- [x] Job semanal automático para seed incremental de novos IPOs
- [x] Backfill histórico de preços com ordenação por tipo
- [x] Fixes de boot sequence, imports e logs de background task
- [x] Frontend: aba **BDR** adicionada no modal de transações

---

## ✅ Sprint 5 — Frontend Dashboard (Concluído — 30/06/2026)
**Período:** Junho–Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [x] **Página de Rentabilidade** (`/carteira/rentabilidade`)
- [x] **Hotfixes Tesouro Direto & Cripto**
- [x] **Fixes CSS/UI Design System**
- [x] **Dashboard principal** (`ResumePage`)
- [x] **Gráfico de rentabilidade mensal + benchmark** (`RentabilidadeChart`)
- [x] **Correção da evolução patrimonial vazia**
- [x] **Fix rentabilidade renda fixa**
- [x] **Fix modal de lançamento — renda fixa sem cotas**
- [x] **Bump dependências frontend e backend**
- [x] **Fix rentabilidade dia/mês/12m + KpiCard Rentabilidade reestruturado**

---

## ✅ Sprint 5A — Botão + Lançamento no Mobile (Concluído — 26/06/2026)
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [x] `BottomNav` adicionado ao `AppLayout`
- [x] FAB 52×52px com elevação visual acima da barra
- [x] Área de toque mínima 44×44px em todos os itens
- [x] `aria-label` em todos os `NavLink`, `nav` e FAB

---

## ✅ Sprint 5E — Distribuição Ideal da Carteira: BDR + Reflexo no Resumo (Concluído — 30/06/2026)
**Período:** Julho 2026 | [Issue #79](https://github.com/lfragoso93-web/sig-v2/issues/79)

- [x] `BDR` adicionado a `VALID_ASSET_CLASSES` e `_TYPE_LABEL` no `class_target_service`
- [x] `get_targets_with_current()` retorna BDR quando há posição ou meta configurada
- [x] `AllocationTargetWidget` itera `rows` dinamicamente
- [x] Widget exibido na `ResumePage` sob o gráfico de distribuição

---

## ✅ Sprint 5F — Sync Semanal de Dividendos de FIIs (Concluído — 30/06/2026)
**Período:** Julho 2026

> Primeira etapa do pipeline de proventos, com sincronização de FIIs via provedor de cotações e job automático semanal.

- [x] Configurações de chunk, retry e bootstrap
- [x] Client de integração com retry exponencial, chunking e DTO interno
- [x] `models/dividends_sync_job.py` + migration `012`: lock distribuído, cursor incremental e métricas por execução
- [x] `services/dividends_sync_service.py`: orquestrador lock → fetch → upsert sem N+1 → release
- [x] Scheduler semanal e endpoints admin de status/disparo manual

---

## ✅ Sprint 5G — Pipeline completo de mercado e proventos RV nacional (Concluído — 04/07/2026)
**Período:** Julho 2026 | [Issue #92](https://github.com/lfragoso93-web/sig-v2/issues/92) | [PR #93](https://github.com/lfragoso93-web/sig-v2/pull/93)

> Entrega concluída após o avanço de proventos: coleta, normalização, materialização e batch incremental para renda variável nacional.

- [x] `asset_dividends` expandido com Data Com, Data Ex, pagamento, aprovação, valor unitário, total, fatores, ISIN, payload bruto e eventos não-cash
- [x] Parser/backfill para dividendos, JCP, rendimentos, amortização, bonificação e subscrição
- [x] Materialização de proventos por carteira usando posição elegível na Data Com
- [x] Pipeline único por ativo: cadastro, preços, logo, eventos corporativos/proventos e materialização
- [x] Onboarding e seed delegando para o pipeline único
- [x] CLIs manuais para sincronização de proventos, pipeline individual e pipeline batch
- [x] Batch incremental diário para ativos mantidos em carteira
- [x] Tabela de Proventos preparada para Data Com e Data Ex separadas
- [x] Testes automatizados para parser/materialização e pipeline batch

---

## ✅ Sprint 6B — PatrimonioPage Analítica + Bugfixes Críticos (Concluído — 30/06/2026)
**Período:** Junho 2026 | [Issue #81](https://github.com/lfragoso93-web/sig-v2/issues/81)

> Reformulação completa da página Patrimônio com foco analítico, correção de bugs críticos e limpeza de arquivos legados.

### Bugfixes
- [x] Migration 022 cria colunas de proventos na tabela `dividends`
- [x] Guards defensivos em `formatPercent`, `formatBRL` e props dos KPIs
- [x] Funções de rentabilidade por ativo/classe adicionadas ao service para resolver boot

### PatrimonioPage — Reformulação
- [x] Aba **Histórico** removida
- [x] **Visão Geral**: KPIs + evolução mensal + donut + widget Distribuição Ideal vs. Atual + tabela de posições
- [x] **Aba Análise**: Score HHI + Top 5 posições + concentração por classe + desvio do alvo
- [x] **Treemap SVG puro** com algoritmo Squarified
- [x] Toggle diário/mensal e seletor de período no gráfico de evolução

### Continuidade
- [ ] Refinar UX em cards e espaçamento visual conforme [issue #90](https://github.com/lfragoso93-web/sig-v2/issues/90)

---

## ✅ Sprint 6C — Limpeza de Rotas e Arquivos Legados (Concluído — 30/06/2026)
**Período:** Junho 2026

- [x] `HistoricoPage.tsx` removido + rota `/carteira/historico` removida do router
- [x] `Login.tsx` e `Register.tsx` duplicados de `auth/` removidos
- [x] `Landing.tsx` restaurado com rota pública `/` em `main.tsx`
- [x] `App.tsx` mantido como legado sem re-export que quebrava o build

---

## 🔄 Sprint corrente — Ajustes pós-proventos, Resumo e UX (Em andamento)
**Período:** Julho 2026

### Resumo — Bugs a corrigir
- [ ] Dropdown/lista suspensa deve extrapolar a área da tabela e permanecer visível mesmo com poucos ativos
- [ ] Cabeçalho/tabela: revisar diferença entre **variação** e **rentabilidade total da classe**
- [ ] KPIs da página Resumo devem refletir apenas valores atuais e preservar sinal negativo quando a carteira estiver negativa
- [ ] Comparar comportamento dos cards com a página Patrimônio, que parece mais consistente

### Proventos — Pós-pipeline
- [ ] Validar tela com dados reais materializados por carteira
- [ ] Revisar filtros, status e agregações após expansão de `asset_dividends`
- [ ] Garantir consistência entre Data Com, Data Ex e Data de Pagamento
- [ ] Conferir cards/resumos de proventos 12m, mês e total líquido

### Revisão visual e responsividade — [Issue #103](https://github.com/lfragoso93-web/sig-v2/issues/103)
- [ ] Fazer auditoria geral da interface para reduzir densidade visual e melhorar espaçamentos
- [ ] Padronizar cards, KPIs, filtros, botões, inputs, badges, tabelas e estados vazios
- [ ] Revisar responsividade em desktop, tablet e mobile nas páginas principais
- [ ] Priorizar Resumo, Patrimônio, Proventos, Transações, Rentabilidade e Configurações
- [ ] Documentar plano e critérios em [`docs/REVISAO_INTERFACE.md`](./docs/REVISAO_INTERFACE.md)

---

## 🔄 Sprint 5B — Performance de Queries (Em andamento)
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

> **Criticidade: Alta | Esforço: Alto | Impacto: Performance**

### Concluído
- [x] `retorno_dia_pct`: usa snapshot imediatamente anterior ao dia atual
- [x] `retorno_mes_pct`: usa 1º do mês calendário como base fixa
- [x] `retorno_dia_pct` adicionado ao tipo `RentabilidadeKpis`
- [x] KpiCard Rentabilidade exibe Hoje / Mês / 12m / Desde o início

### Pendente
- [ ] Mapear queries com tempo de execução elevado (`EXPLAIN ANALYZE`)
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

## 📋 Sprint 6 — Qualidade Visual & Rename SGI (Planejado)
**Período:** Julho–Agosto 2026 | [Issue #55](https://github.com/lfragoso93-web/sig-v2/issues/55)

### Sprint 6A — Remoção de Referências a APIs Externas

> **Criticidade: Alta | Esforço: Baixo | Impacto: Segurança / Compliance**

- [ ] Remover menções explícitas a nomes de provedores em documentação pública
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
- [ ] Criar modelo `AuditLog` (user_id, action, resource, timestamp, metadata)
- [ ] Middleware ou decorator para captura automática de escrita
- [ ] Endpoint `GET /admin/users/{id}/audit` para superadmin
- [ ] Tela de auditoria no painel admin
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
- [ ] Deploy em ambiente de produção
- [ ] Monitoramento de erros
- [ ] Documentação da API
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
