# Roadmap de Sprints — SGI v2

> Última atualização: 07/07/2026
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

- [x] Módulo goals
- [x] Módulo IRPF base
- [x] Módulo analysis base
- [x] Módulo fixed_income
- [x] Módulo quotes
- [x] Módulo prices
- [x] Módulo class_targets
- [x] Asset onboarding service

---

## ✅ Sprint 4 — Catálogo de Ativos e Dados (Concluído)
**Período:** Junho 2026 (2ª quinzena) — concluído em 24/06/2026 | [Issue #53](https://github.com/lfragoso93-web/sig-v2/issues/53)

- [x] `asset_seed_service` com UPSERT idempotente
- [x] Endpoint superadmin para seed de ativos
- [x] Job semanal automático para seed incremental
- [x] Backfill histórico de preços com ordenação por tipo
- [x] Correções de boot sequence, imports e logs de background task
- [x] Aba **BDR** adicionada no modal de transações

---

## ✅ Sprint 5 — Frontend Dashboard (Concluído — 30/06/2026)
**Período:** Junho–Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [x] Página de Rentabilidade
- [x] Hotfixes Tesouro Direto & Cripto
- [x] Fixes CSS/UI Design System
- [x] Dashboard principal (`ResumePage`)
- [x] Gráfico de rentabilidade mensal + benchmark
- [x] Correção da evolução patrimonial vazia
- [x] Fix rentabilidade renda fixa
- [x] Fix modal de lançamento — renda fixa sem cotas
- [x] Bumps de dependências frontend e backend
- [x] Fix rentabilidade dia/mês/12m + KpiCard Rentabilidade reestruturado

---

## ✅ Sprint 5A — Botão + Lançamento no Mobile (Concluído — 26/06/2026)
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [x] `BottomNav` adicionado ao `AppLayout`
- [x] FAB 52×52px com elevação visual acima da barra
- [x] Área de toque mínima 44×44px
- [x] `aria-label` em todos os `NavLink`, `nav` e FAB

---

## ✅ Sprint 5E — Distribuição Ideal da Carteira: BDR + Reflexo no Resumo (Concluído — 30/06/2026)
**Período:** Julho 2026 | [Issue #79](https://github.com/lfragoso93-web/sig-v2/issues/79)

- [x] `BDR` adicionado a `VALID_ASSET_CLASSES` e `_TYPE_LABEL`
- [x] `get_targets_with_current()` retorna BDR quando há posição ou meta configurada
- [x] `AllocationTargetWidget` itera linhas dinamicamente
- [x] Widget exibido na `ResumePage`

---

## ✅ Sprint 5F — Sync Semanal de Dividendos de FIIs (Concluído — 30/06/2026)
**Período:** Julho 2026

- [x] Configurações de chunk, retry e bootstrap
- [x] Client de integração com retry exponencial, chunking e DTO interno
- [x] Modelo de job de sync com lock distribuído, cursor incremental e métricas
- [x] Orquestrador lock → fetch → upsert → release
- [x] Scheduler semanal e endpoints admin de status/disparo manual

---

## ✅ Sprint 5G — Pipeline completo de mercado e proventos RV nacional (Concluído — 04/07/2026)
**Período:** Julho 2026 | [Issue #92](https://github.com/lfragoso93-web/sig-v2/issues/92) | [PR #93](https://github.com/lfragoso93-web/sig-v2/pull/93)

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

## ✅ Sprint 5H — Validação da tela Proventos pós-pipeline (Concluído — 06/07/2026)
**Período:** Julho 2026 | [Issue #95](https://github.com/lfragoso93-web/sig-v2/issues/95)

- [x] Agregações de proventos revisadas para Data Com com Data Ex como fallback
- [x] Eventos não-cash excluídos dos totais financeiros sem quebrar a listagem
- [x] `summary` com filtros de status, ano, classe de ativo e tipo de evento
- [x] KPIs de Proventos sincronizados com os filtros da tabela
- [x] Tabela de Proventos simplificada com remoção da coluna técnica “Natureza”
- [x] Testes de cash vs. não-cash, elegibilidade por Data Com e agregações
- [x] Ajustes pontuais em Transações para botões de ação da tabela

---

## ✅ Sprint 5I — Estabilização auth, dependências e CI (Concluído — 07/07/2026)
**Período:** Julho 2026

- [x] Corrigido fluxo “Esqueci senha” com endpoints backend `forgot/reset password`
- [x] Corrigido prefixo duplicado `/api/v1` no frontend de recuperação de senha
- [x] Criado endpoint autenticado `PATCH /users/me/password`
- [x] Validada alteração de senha em Configurações
- [x] Corrigido build Vite no Docker removendo `--configLoader native`
- [x] Aplicadas e validadas pendências Dependabot de backend, frontend e CI
- [x] Atualizadas Actions centrais do workflow de CI
- [x] Validação local: Docker Compose, login, recuperação de senha, troca de senha e Vitest

---

## ✅ Sprint 6B — PatrimonioPage Analítica + Bugfixes Críticos (Concluído — 30/06/2026)
**Período:** Junho 2026 | [Issue #81](https://github.com/lfragoso93-web/sig-v2/issues/81)

- [x] Migration 022 cria colunas de proventos na tabela `dividends`
- [x] Guards defensivos em formatações e props dos KPIs
- [x] Funções de rentabilidade por ativo/classe adicionadas ao service
- [x] Aba Histórico removida
- [x] Visão Geral com KPIs, evolução mensal, donut, distribuição ideal vs. atual e tabela de posições
- [x] Aba Análise com Score HHI, Top 5 posições, concentração por classe e desvio do alvo
- [x] Treemap SVG puro com algoritmo Squarified

---

## ✅ Sprint 6C — Limpeza de Rotas e Arquivos Legados (Concluído — 30/06/2026)
**Período:** Junho 2026

- [x] `HistoricoPage.tsx` removido + rota `/carteira/historico` removida
- [x] `Login.tsx` e `Register.tsx` duplicados de `auth/` removidos
- [x] `Landing.tsx` restaurado com rota pública `/`
- [x] `App.tsx` mantido como legado sem re-export que quebrava o build

---

## ✅ Sprint 6E — Revisão visual e responsividade (Concluído — 06/07/2026)
**Período:** Julho 2026 | [Issue #103](https://github.com/lfragoso93-web/sig-v2/issues/103) | PRs #104–#108

- [x] Auditoria geral da interface para reduzir densidade visual e melhorar espaçamentos
- [x] Padronização de cards, KPIs, filtros, botões, inputs, badges, tabelas e estados vazios
- [x] Responsividade revisada em desktop, tablet, mobile e telas ultrawide
- [x] Resumo, Patrimônio, Proventos, Transações, Rentabilidade e Configurações revisadas
- [x] Plano e critérios documentados em [`docs/REVISAO_INTERFACE.md`](./docs/REVISAO_INTERFACE.md)

---

## 🔄 Próxima sprint — Contratos operacionais e admin
**Período:** Julho 2026

### CSV — [Issue #82](https://github.com/lfragoso93-web/sig-v2/issues/82)
- [ ] Corrigir importação CSV autenticada usando client com Bearer token
- [ ] Enviar `dry_run=false` no fluxo de importação real
- [ ] Corrigir template CSV para resposta compatível com streaming/download
- [ ] Validar fluxo completo no modal de importação

### Backup/Restore — [Issue #83](https://github.com/lfragoso93-web/sig-v2/issues/83)
- [ ] Criar endpoint autenticado para download de backup
- [ ] Endurecer restore com senha/frase de confirmação
- [ ] Adicionar lock global para evitar restores concorrentes
- [ ] Preparar trilha de auditoria e status de operação
- [ ] Revisar storage persistente para backups

### Admin — [Issue #98](https://github.com/lfragoso93-web/sig-v2/issues/98)
- [ ] Revisar endpoints administrativos de usuários
- [ ] Revisar autorização de superadmin
- [ ] Permitir edição de dados permitidos de usuários
- [ ] Permitir alteração de perfil/permissão quando aplicável
- [ ] Proteger contra remoção acidental do último superadmin

### Compliance — [Issue #80](https://github.com/lfragoso93-web/sig-v2/issues/80)
- [ ] Remover menções explícitas a provedores em documentação pública
- [ ] Substituir referências por termos genéricos
- [ ] Revisar Swagger/OpenAPI e mensagens públicas

### Auth — [Issue #97](https://github.com/lfragoso93-web/sig-v2/issues/97)
- [ ] Implementar login/cadastro com Google OAuth como método adicional
- [ ] Vincular usuário existente por e-mail verificado
- [ ] Emitir os mesmos tokens internos do login tradicional

---

## 🔄 Sprint 5B — Performance de Queries (Em andamento)
**Período:** Julho 2026 | [Issue #54](https://github.com/lfragoso93-web/sig-v2/issues/54)

- [x] `retorno_dia_pct` usa snapshot imediatamente anterior ao dia atual
- [x] `retorno_mes_pct` usa 1º do mês calendário como base fixa
- [x] `retorno_dia_pct` adicionado ao tipo `RentabilidadeKpis`
- [x] KpiCard Rentabilidade exibe Hoje / Mês / 12m / Desde o início
- [ ] Mapear queries com tempo de execução elevado (`EXPLAIN ANALYZE`)
- [ ] Adicionar índices faltantes e otimizar joins
- [ ] Revisar N+1 em listagens de posições e transações

---

## 📋 Sprint 6 — Qualidade Visual & Rename SGI (Planejado)
**Período:** Julho–Agosto 2026 | [Issue #55](https://github.com/lfragoso93-web/sig-v2/issues/55)

### Sprint 6A — Remoção de Referências a APIs Externas
- [ ] Remover menções explícitas a nomes de provedores em documentação pública
- [ ] Substituir referências por termos genéricos: “provedor de cotações”, “serviço de câmbio”
- [ ] Manter nomes técnicos apenas em `.env.example` com comentários de propósito
- [ ] Revisar Swagger/OpenAPI
- [ ] Análise de impacto para rename SIG v2 → SGI

### Sprint 6D — Import de Ativos via CSV
- [ ] Definir schema do CSV modelo
- [ ] Endpoint para baixar CSV modelo
- [ ] Endpoint para validar e importar ativos em massa
- [ ] Validação linha a linha com relatório de erros
- [ ] Importação atômica
- [ ] Frontend com modal de preview e download do modelo

---

## 📋 Sprint 7 — Módulo de IRPF (Planejado)
**Período:** Agosto 2026 | [Issue #56](https://github.com/lfragoso93-web/sig-v2/issues/56)

- [ ] Completar `IRPFPage.tsx`
- [ ] Exportação de relatório mensal/anual (PDF ou CSV)
- [ ] Cálculo consolidado por ano-calendário
- [ ] Isenção para vendas até R$20.000/mês
- [ ] Apuração Day Trade vs Swing Trade
- [ ] Testes de validação do cálculo de ganho de capital

### Sprint 7B — Logs de Auditoria por Usuário
- [ ] Criar modelo `AuditLog`
- [ ] Captura automática de escrita
- [ ] Endpoint para superadmin consultar auditoria
- [ ] Tela de auditoria no painel admin
- [ ] Exportação de log em CSV

---

## 📋 Sprint 8 — Análise de Carteira (Planejado)
**Período:** Agosto–Setembro 2026 | [Issue #57](https://github.com/lfragoso93-web/sig-v2/issues/57)

- [ ] Completar `AnalisePage.tsx`
- [ ] Score de diversificação por setor e classe
- [ ] Concentração por ativo com alertas
- [ ] Comparação vs. metas de alocação
- [ ] Sugestões de rebalanceamento

---

## 📋 Sprint 9 — Janela Global do Ativo (Planejado)
**Período:** Setembro 2026 | [Issue #58](https://github.com/lfragoso93-web/sig-v2/issues/58)

- [ ] Componente `AssetDetailDrawer.tsx`
- [ ] Gráfico de preço histórico
- [ ] Histórico de proventos do ativo
