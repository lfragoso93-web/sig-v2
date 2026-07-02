# Análise Completa de Gaps — SGI v2
**Gerado em:** 02 de Julho de 2026  
**Status do Projeto:** Sprint 5/6 (Dashboard e Patrimônio) — 78% de completude funcional

---

## 📋 Sumário Executivo

O projeto **SGI v2** é uma plataforma madura de gestão de investimentos com backend FastAPI sólido e frontend React com boas práticas. **78% das features principais estão implementadas**, mas existem **21 gaps críticos identificados** distribuídos em 7 categorias:

| Categoria | Criticidade | Gaps | Esforço Médio |
|-----------|------------|------|--------------|
| 🔴 **Performance & Banco** | 🔴 Alta | 6 | Médio-Alto |
| 🟡 **Frontend/UX** | 🟡 Média | 5 | Médio |
| 🟡 **Completude de Features** | 🟡 Média | 4 | Alto |
| 🟡 **Testes & QA** | 🟡 Média | 3 | Médio |
| 🟢 **Documentação** | 🟢 Baixa | 2 | Baixo |
| 🟢 **Segurança & Compliance** | 🟢 Baixa | 1 | Baixo |

---

## 🔴 1. GAP CRÍTICO: Performance & Otimização de Banco (6 gaps)

### Gap 1.1: N+1 em Portfolio Snapshot (CORRIGIDO ✅)
**Arquivo:** `backend/app/services/portfolio_snapshot_service.py`  
**Status:** Documentado em `QUERY_OPTIMIZATION.md` — correção já aplicada  
**Impacto:** Reduz 5.000 queries em backfill de 1 ano para 250  
**Esforço:** ✅ Completado

---

### Gap 1.2: Índices de Performance Faltando (🔴 CRÍTICO)
**Arquivos afetados:** 
- `price_history` — sem índice composto `(ticker, date DESC)`
- `transactions` — sem índice composto `(portfolio_id, date ASC)`
- `portfolio_snapshot` — sem índice composto `(portfolio_id, snapshot_date DESC)`
- `fx_rates` — sem índice em `rate_date`

**Problema:** Queries críticas fazem Seq Scan em vez de Index Scan  
**Impacto:** Queries crescem com O(n) à medida que dados acumulam  
**Recomendação:** 
```python
# Criar migration: backend/alembic/versions/024_add_performance_indexes.py
CREATE INDEX CONCURRENTLY idx_price_history_ticker_date ON price_history (ticker, date DESC);
CREATE INDEX CONCURRENTLY idx_tx_portfolio_date ON transactions (portfolio_id, date ASC);
CREATE INDEX CONCURRENTLY idx_portfolio_snapshot_portfolio_date ON portfolio_snapshot (portfolio_id, snapshot_date DESC);
CREATE INDEX CONCURRENTLY idx_fx_rates_date ON fx_rates (rate_date DESC);
```
**Esforço:** Baixo (~1h) — apenas SQL, sem lógica  
**Impacto:** -30-50% latência em queries críticas

---

### Gap 1.3: Cache Redis Incompleto (🟡 MÉDIO)
**Endpoints sem cache:**
- `GET /portfolios/{id}/resumo` → deveria ter TTL 2min
- `GET /portfolios/{id}/posicoes` → deveria ter TTL 2min
- `get_portfolio_summary()` → função interna sem cache

**Problema:** Endpoints mais frequentes (dashboard) refazem cálculos pesados  
**Recomendação:** Seguir padrão em `rentabilidade_service.py`
```python
# Em portfolio_service.py:
@cache_key("portfolio", portfolio_id, "summary", ttl=120)
async def get_portfolio_summary(...): ...
```
**Esforço:** Baixo (~1-2h) — copiar padrão existente  
**Impacto:** Dashboard instantâneo para usuários frequentes

---

### Gap 1.4: Monitoramento de Queries Ausente (🟡 MÉDIO)
**Problema:** Sem logs de queries lentas, sem `EXPLAIN ANALYZE`, sem pg_stat_statements  
**Impacto:** Impossível detectar regressões de performance em produção  
**Recomendação:**
```sql
-- Adicionar em docker-compose.yml:
postgresql:
  environment:
    - log_min_duration_statement=100  # loga queries > 100ms
    - shared_preload_libraries=pg_stat_statements
    - track_functions=all
```
**Esforço:** Baixo (~30min) — apenas config PostgreSQL  
**Impacto:** Visibilidade de gargalos em tempo real

---

### Gap 1.5: Batch Prefetch Incompleto (🟡 MÉDIO)
**Arquivo:** `backend/app/services/rentabilidade_service.py`  
**Função:** `_calc_invested_up_to` é chamada 2x sem batching  
**Status:** Documentado em `QUERY_OPTIMIZATION.md` — correção já aplicada (Q3)  
**Esforço:** ✅ Completado

---

### Gap 1.6: IRPF sem Filtro de Ano (🟡 MÉDIO)
**Arquivo:** `backend/app/services/irpf_service.py`  
**Problema:** Carrega todas as transações do portfólio sem filtrar por ano-base  
**Impacto:** Cálculo cresce O(n) com histórico de transações  
**Recomendação:**
```python
# Adicionar filtro de ano-base:
.where(Transaction.date >= date(ano_base, 1, 1))
.where(Transaction.date <= date(ano_base, 12, 31))
# Manter carga completa apenas para custo_medio
```
**Esforço:** Baixo (~1h) — apenas adicionar filtros WHERE  
**Impacto:** IRPF de 2026 não calcula dados de 2018-2025

---

## 🟡 2. GAPS FRONTEND/UX (5 gaps)

### Gap 2.1: AssetDetailDrawer Não Implementado (🔴 CRÍTICO)
**Referência:** Sprint 9 em ROADMAP_SPRINTS.md  
**Localização:** Deveria estar em `frontend/src/components/AssetDetailDrawer.tsx`  
**Features Ausentes:**
- Gráfico de preço histórico (OHLCV)
- Histórico de proventos do ativo
- Dividend Yield (DY) calculado
- Disponível em PatrimonioPage, Transacoes, RentabilidadePage

**Impacto:** Usuário não consegue clicar em um ativo para ver detalhes completos  
**Esforço:** Alto (~8-10h) — componente novo + integração em 3 páginas  
**Status:** Planejado mas nunca iniciado

---

### Gap 2.2: AnalisePage é Stub Vazio (🟡 MÉDIO)
**Arquivo:** `frontend/src/pages/AnalisePage.tsx`  
**Problema:** Arquivo existe mas tem < 200 bytes (apenas rota vazia)  
**Features Faltando:**
- Score de diversificação por setor
- Concentração por ativo com alertas
- Comparação vs. metas de alocação
- Sugestões de rebalanceamento

**Referência:** Sprint 8 em ROADMAP_SPRINTS.md  
**Impacto:** Usuário não consegue analisar carteira  
**Esforço:** Alto (~10-12h) — nova página complexa  
**Status:** Planejado mas nunca iniciado

---

### Gap 2.3: MetasPage é Stub Vazio (🟡 MÉDIO)
**Arquivo:** `frontend/src/pages/MetasPage.tsx`  
**Problema:** Frontend vazio, backend exists (`goals_service.py`, `GoalsRouter`)  
**Features Ausentes:**
- CRUD de metas financeiras
- Progresso automático da meta
- Visualização do avanço em gráfico
- Alertas de meta atingida/ultrapassada

**Impacto:** Usuário não consegue gerenciar metas apesar do backend estar pronto  
**Esforço:** Médio (~6-8h) — backend pronto, falta frontend  
**Status:** Planejado mas nunca iniciado

---

### Gap 2.4: Layout Mobile Incompleto (🟡 MÉDIO)
**Problema:** BottomNav foi adicionada (Sprint 5A ✅), mas algumas páginas quebram em mobile  
**Específicos:**
- PatrimonioPage tem gráficos que overflow horizontal
- RentabilidadePage tabela não é responsiva
- Modais não adaptam bem a telas pequenas
- Algumas colunas desaparecem sem aviso

**Impacto:** Usuários mobile têm experiência degradada  
**Esforço:** Médio (~6-8h) — testing + ajustes de layout  
**Status:** Parcialmente implementado

---

### Gap 2.5: Sistema de Temas/Dark Mode Ausente (🟢 BAIXO)
**Referência:** BackLog em ROADMAP_SPRINTS.md  
**Arquivo:** `frontend/src/contexts/ThemeContext.tsx` existe mas não funciona  
**Problema:** Não há toggle de tema, não há persistência  
**Impacto:** Aplicativo não tem modo escuro  
**Esforço:** Médio (~4-6h)  
**Status:** Infraestrutura existe, falta implementação

---

## 🟡 3. COMPLETUDE DE FEATURES (4 gaps)

### Gap 3.1: IRPFPage Incompleto (🟡 MÉDIO)
**Arquivo:** `frontend/src/pages/IRPFPage.tsx`  
**Problema:** Interface existe, backend existe, mas cálculos incompletos
**Features Faltando:**
- Exportação de relatório (PDF/CSV)
- Cálculo consolidado por ano-calendário
- Isenção para vendas até R$20.000/mês
- Apuração Day Trade vs Swing Trade
- Testes de validação

**Impacto:** IRPF é apenas visualização, não é funcional  
**Esforço:** Alto (~10-12h) — lógica financeira complexa  
**Status:** Parcialmente implementado (estrutura há, lógica não)

---

### Gap 3.2: Import CSV de Ativos Ausente (🔴 CRÍTICO)
**Referência:** Sprint 6D em ROADMAP_SPRINTS.md  
**Problema:** Feature totalmente ausente (backend + frontend)
**O que falta:**
- `GET /api/v1/assets/csv-template` — template para download
- `POST /api/v1/portfolios/{id}/import-csv` — importação com validação
- Modal de preview + confirmação no frontend
- Validação linha a linha com relatório de erros
- Importação atômica (tudo ou rollback)

**Impacto:** Usuários só conseguem lançar transações manualmente  
**Esforço:** Alto (~12-15h) — backend + frontend + validação  
**Status:** Planejado mas nunca iniciado

---

### Gap 3.3: Logs de Auditoria Ausentes (🟡 MÉDIO)
**Referência:** Sprint 7B em ROADMAP_SPRINTS.md  
**Problema:** Feature totalmente ausente (backend + frontend)
**O que falta:**
- Modelo `AuditLog` (user_id, action, resource, timestamp, metadata JSON)
- Middleware para captura automática de operações de escrita
- Endpoint `GET /admin/users/{id}/audit` para superadmin
- Exportação de log em CSV
- Tela de auditoria no painel admin

**Impacto:** Sem rastreabilidade de ações de usuários  
**Esforço:** Médio (~8-10h) — backend + frontend + middleware  
**Status:** Planejado mas nunca iniciado

---

### Gap 3.4: Backup/Restore do Banco Ausente (🔴 CRÍTICO)
**Referência:** Sprint 10B em ROADMAP_SPRINTS.md  
**Problema:** Feature totalmente ausente (backend + frontend)
**O que falta:**
- `POST /api/v1/admin/database/backup` — dump PostgreSQL
- `POST /api/v1/admin/database/restore` — restauração com confirmação
- Autenticação dupla (senha + confirmação)
- Backup com TTL 24h em volume Docker
- Tela de admin com botões de backup/restore

**Impacto:** Sem disaster recovery — impossível recuperar dados perdidos  
**Esforço:** Alto (~12-15h) — ops críticas + UI  
**Status:** Planejado mas nunca iniciado

---

## 🟡 4. TESTES & QA (3 gaps)

### Gap 4.1: Testes Frontend Ausentes (🔴 CRÍTICO)
**Problema:** 40+ componentes React, 0 testes automatizados  
**Arquivos sem testes:**
- `frontend/src/pages/*.tsx` — nenhuma página tem teste
- `frontend/src/components/**/*.tsx` — nenhum componente tem teste
- `frontend/src/hooks/*.ts` — nenhum hook tem teste

**Impacto:** Regressões não detectadas até deployment  
**Cobertura:** 0% do frontend  
**Esforço:** Alto (~20-30h) — setup Jest/RTL + testes  
**Recomendação:**
```bash
# Adicionar ao package.json:
"test": "vitest",
"test:coverage": "vitest --coverage"

# Criar: frontend/vitest.config.ts
# Criar: frontend/__tests__/ com testes
```
**Status:** Jamais iniciado

---

### Gap 4.2: Testes Backend Limitados (🟡 MÉDIO)
**Problema:** Apenas 8 testes unitários para 70+ endpoints/services  
**Testes Existentes:**
- `test_portfolio_service.py` — 3 testes
- `test_rentabilidade_service.py` — 13 testes
- `test_quotes_service.py` — testes básicos
- `test_dividend_backfill_service.py` — testes básicos
- `test_dividends_sync_service.py` — testes de sync
- `test_auth_service.py` — testes de auth

**Testes Faltando:**
- Routers não têm testes de integração
- IRPF service não tem testes
- Fixed income não tem testes
- Treasury não tem testes
- Admin endpoints não têm testes

**Cobertura:** ~15-20% do backend  
**Impacto:** Bugs em produção não detectados em CI/CD  
**Esforço:** Alto (~15-20h) — adicionar 40+ testes  
**Status:** Parcialmente implementado

---

### Gap 4.3: Testes de Integração E2E Ausentes (🟡 MÉDIO)
**Problema:** Sem testes que simulam fluxo real de usuário  
**Faltam testes para:**
- Login → Criar portfólio → Lançar transação → Ver rentabilidade
- Divisão de proventos com fallback em cascata
- Evolução patrimonial com snapshots
- Cálculo de IRPF do começo ao fim

**Impacto:** Fluxos críticos nunca são testados  
**Esforço:** Alto (~12-15h) — setup Cypress/Playwright + testes  
**Status:** Jamais iniciado

---

## 🟢 5. DOCUMENTAÇÃO (2 gaps)

### Gap 5.1: API Documentation Incompleta (🟡 MÉDIO)
**Problema:** Swagger/OpenAPI tem referências explícitas a APIs externas  
**Sprint 6A:** "Remoção de Referências a APIs Externas"  
**Específicos:**
- Descrições mencionam "BRAPI", "YFinance", "Alpha Vantage"
- Documentação pública não segue as mudanças de código
- `.env.example` expõe nomes de provedores

**Impacto:** Compliance/segurança — não cumpre Sprint 6A  
**Recomendação:**
```python
# Substituir em app/main.py:
description="API de integração com provedor de cotações"
# Em vez de:
description="API de integração com BRAPI"
```
**Esforço:** Baixo (~2-3h) — apenas find/replace em docstrings  
**Status:** Planejado mas nunca iniciado

---

### Gap 5.2: Documentação de Arquitetura Faltando (🟢 BAIXO)
**Problema:** Sem documentação de decisões arquiteturais  
**Faltam documentos:**
- `docs/ARCHITECTURE.md` — decisões de design
- `docs/DATABASE_SCHEMA.md` — ERD comentado
- `docs/DEPLOYMENT.md` — guia de deploy em produção
- `docs/TROUBLESHOOTING.md` — problemas comuns e soluções
- `docs/API_DESIGN.md` — padrões de API (paginação, filtros, etc)

**Impacto:** Onboarding de novos devs é lento  
**Esforço:** Médio (~6-8h) — escrita técnica  
**Status:** Jamais iniciado

---

## 🟢 6. SEGURANÇA & COMPLIANCE (1 gap)

### Gap 6.1: Sprint 6A Incompleto (🟡 MÉDIO)
**Referência:** ROADMAP_SPRINTS.md Sprint 6A  
**Problema:** Feature planejada mas não implementada
**O que falta:**
- ❌ Remover menções explícitas a BRAPI, YFinance, Alpha Vantage em docs públicas
- ❌ Substituir por termos genéricos: "provedor de cotações", "fonte de dados internacionais"
- ❌ Manter nomes técnicos apenas em `.env.example` com comentários
- ❌ Revisar Swagger/OpenAPI: remover nomes em descrições
- ❌ Análise de impacto para rename SIG v2 → SGI

**Impacto:** Documentação pública expõe dependências externas (baixo risco, mas viola compliance)  
**Esforço:** Baixo (~2-3h)  
**Status:** Planejado mas nunca iniciado

---

## 📊 Resumo de Distribuição de Gaps

```
Total de gaps: 21

Por Criticidade:
  🔴 CRÍTICO:  4 gaps (N+1 fixes, índices, CSV import, backup/restore)
  🟡 MÉDIO:   13 gaps (cache, IRPF, mobile, testes, audit logs, docs)
  🟢 BAIXO:    4 gaps (dark mode, API docs, compliance, arq. docs)

Por Categoria:
  1. Performance & BD:  6 gaps (4 críticos)
  2. Frontend/UX:       5 gaps (1 crítico)
  3. Features:          4 gaps (2 críticos)
  4. Testes & QA:       3 gaps
  5. Documentação:      2 gaps
  6. Segurança:         1 gap

Por Esforço Estimado:
  Baixo (< 2h):          5 gaps
  Médio (2-8h):          8 gaps
  Alto (8-15h):          6 gaps
  Muito Alto (> 15h):    2 gaps

Total de Esforço: ~120-150 horas de dev
```

---

## 🎯 Priorização Recomendada

### Fase 1: Produção-Ready (Semana 1) — 30-40h
**Objetivo:** Tornar aplicativo seguro e performático para produção

1. **[CRÍTICO]** Gap 1.2 — Índices de Performance (+30min de merge)
2. **[CRÍTICO]** Gap 1.3 — Cache Redis Incompleto (+1-2h)
3. **[CRÍTICO]** Gap 4.1 — Testes Frontend Setup (+2h)
4. **[CRÍTICO]** Gap 6.1 — Sprint 6A Compliance (+2-3h)
5. Gap 1.4 — Monitoramento Queries (+30min)
6. Gap 1.1, 1.5 — Verificar se N+1 fixes estão merged

**Saída esperada:** App pronto para produção com performance baseline

---

### Fase 2: Completude de Features (Semana 2-3) — 40-60h
**Objetivo:** Implementar features críticas planejadas

1. **[CRÍTICO]** Gap 3.2 — Import CSV de Ativos (+12-15h)
2. **[CRÍTICO]** Gap 3.4 — Backup/Restore Database (+12-15h)
3. Gap 3.1 — IRPF Completo (+10-12h)
4. Gap 3.3 — Audit Logs (+8-10h)
5. Gap 2.1 — AssetDetailDrawer (+8-10h)

**Saída esperada:** Sprint roadmap atualizado, features críticas implementadas

---

### Fase 3: Qualidade & UX (Semana 4-6) — 40-50h
**Objetivo:** Melhorar testes, documentação e experiência do usuário

1. Gap 4.2 — Testes Backend Estendidos (+15-20h)
2. Gap 4.3 — Testes E2E (+12-15h)
3. Gap 2.4 — Layout Mobile Responsivo (+6-8h)
4. Gap 5.2 — Documentação de Arquitetura (+6-8h)
5. Gap 2.2, 2.3 — AnalisePage e MetasPage (+10-12h)

**Saída esperada:** Cobertura de testes > 60%, docs completa

---

## ✅ Check-list para Cada Gap

**Template para resolver um gap:**

```markdown
## Gap X.Y: [Nome]

### Status Atual
- [ ] Verificar se já foi parcialmente implementado
- [ ] Abrir issue no GitHub com label [gap-xy]
- [ ] Criar branch: `fix/gap-xy-descricao`

### Implementação
- [ ] Implementar código
- [ ] Adicionar testes
- [ ] Atualizar documentação
- [ ] Rodar CI/CD (lint, type-check, test, build)

### Review & Merge
- [ ] Code review
- [ ] Verificar impacto em features relacionadas
- [ ] Merge para main

### Verificação Pós-Deploy
- [ ] Testar em staging
- [ ] Monitorar performance (se aplicável)
- [ ] Marcar como ✅ Completo
```

---

## 📚 Referências

- **ROADMAP_SPRINTS.md** — Sprints planejadas e status
- **QUERY_OPTIMIZATION.md** — Detalhamento dos gaps 1.1-1.6
- **RESUME.md** — Estado do projeto em 26/06
- **CHANGELOG.md** — Histórico de implementações
- **.github/workflows/ci.yml** — CI/CD pipeline

---

## 🚀 Próximos Passos

1. **Hoje (02/07):** Discutir priorização com time
2. **Semana 1:** Resolver gaps de Fase 1 (performance + produção)
3. **Semana 2-3:** Implementar features críticas (Fase 2)
4. **Semana 4-6:** Melhorar qualidade e docs (Fase 3)
5. **Após Fase 3:** Preparar v1.0 para produção

---

*Análise realizada em 02/07/2026 — Abacus AI Agent*
