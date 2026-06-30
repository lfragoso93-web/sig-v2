# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Unreleased] — branch `stable-15jun`

### Planejado — Remoção de Menções a APIs Externas (Sprint 6A)

> Criticidade: **Alta** | Esforço: Baixo | Impacto: Segurança / Compliance

**Documentação pública (README, CHANGELOG, ROADMAP)**
- Substituir todos os nomes explícitos de APIs externas por termos genéricos
- Exemplo: "provedor de cotações", "fonte de dados internacionais"
- Manter nomes técnicos apenas em `.env.example` com comentários descritivos

**`backend/app/` (Swagger/OpenAPI)**
- Remover nomes de provedores em descrições de endpoints e schemas

---

### Planejado — Otimização de Queries (Sprint 5B — pendente)

> Criticidade: **Alta** | Esforço: Alto | Impacto: Performance geral

**`backend/app/`**
- Mapear todas as queries críticas com `EXPLAIN ANALYZE`
- Adicionar índices faltantes em colunas de filtro frequente
- Corrigir padrões N+1 em listagens de posições e transações
- Revisar joins em `rentabilidade_service`, `portfolio_class_evolution_service`
- Documentar queries e tempos de execução antes e depois das otimizações

---

### Planejado — Import de Ativos via CSV (Sprint 6D)

> Criticidade: **Alta** | Esforço: Médio | Impacto: UX / Onboarding

**Backend**
- `GET /api/v1/assets/csv-template` — retorna CSV modelo para download pelo usuário
- `POST /api/v1/portfolios/{id}/import-csv` — valida e importa ativos em lote
- Validação linha a linha com relatório de erros detalhado
- Importação atômica (tudo ou rollback)

**Frontend**
- Botão "Importar via CSV" na tela de transações
- Modal com preview das linhas + confirmação antes de importar
- Download do modelo CSV diretamente no modal

---

### Planejado — Logs de Auditoria por Usuário (Sprint 7B)

> Criticidade: Média | Esforço: Médio | Impacto: Governança interna

**Backend**
- Modelo `AuditLog` (user_id, action, resource, timestamp, metadata JSON)
- Middleware para captura automática de operações de escrita
- Endpoint `GET /admin/users/{id}/audit` para superadmin com filtros
- Exportação de log em CSV

**Frontend**
- Tela de auditoria no painel superadmin (tabela com filtros por usuário, data, ação)

---

### Planejado — Backup e Restore do Banco via Sistema (Sprint 10B)

> Criticidade: **Alta** | Esforço: Médio-Alto | Impacto: Resiliência / Disaster Recovery

**Backend**
- `POST /api/v1/admin/database/backup` — gera dump PostgreSQL e retorna arquivo para download (superadmin)
- `POST /api/v1/admin/database/restore` — recebe arquivo de backup e restaura (superadmin + confirmação por senha)
- Backup armazenado em volume Docker com TTL de 24h
- Todas as operações registradas no `AuditLog`
- Testes de integração: ciclo backup → restore → verificação de integridade

**Frontend**
- Painel de administração com botões de backup e restore
- Modal de confirmação com aviso de impacto antes do restore

---

### Corrigido — Sprint 6B: bugs de boot + crash frontend + PatrimonioPage analítica (30/06/2026)

> Dois bugs críticos diagnosticados e corrigidos + reformulação completa da página Patrimônio.

**Bug 1 — Backend: `payment_date` ausente no banco (migration faltante)**

`backend/alembic/versions/022_add_dividend_payment_date.py` *(novo)*
- Migration 022 criada: adiciona colunas `payment_date`, `ex_date`, `value_per_unit`, `total_received` e `dividend_type` à tabela `dividends`
- Resolve `_proventos_total` no `rentabilidade_service`: filtro `since` por `payment_date` agora funciona corretamente
- Docstring do service atualizado com histórico do fix

**Bug 2 — Frontend: crash `Cannot read properties of undefined (reading 'toFixed')`**

`frontend/src/pages/PatrimonioPage.tsx`
- Guards defensivos `(Number(v) || 0)` aplicados em todos os `.toFixed()` antes de `formatPercent` e `formatBRL`
- `safeNum()` aplicado nos props `change` dos `KpiCard` para valores que podem vir `undefined` da API
- `formatPercent` e `formatBRL`: guard no nível da função — nunca recebem `undefined`

**Bug 3 — Backend: `ImportError` no boot (`get_rentabilidade_por_ativo` não exportada)**

`backend/app/services/rentabilidade_service.py`
- Funções `get_rentabilidade_por_ativo` e `get_rentabilidade_por_classe` adicionadas ao service
- Impedia o boot completo do servidor FastAPI

**Sprint 6B — Reformulação da `PatrimonioPage`**

`frontend/src/pages/PatrimonioPage.tsx`
- **Aba removida**: Histórico (duplicava conteúdo da RentabilidadePage)
- **Visão Geral**: KPIs da carteira + evolução mensal em barras + donut de alocação por classe + widget de Distribuição Ideal vs. Atual + tabela de posições
- **Aba Análise**: Score HHI com nível de risco (baixo/moderado/alto/crítico) + Top 5 posições por peso + concentração por classe (donut + barras horizontais por ativo dentro de cada classe) + desvio do alvo por classe
- **Treemap SVG puro** com algoritmo Squarified: visualização de concentração sem dependências externas
- **Toggle diário/mensal** e seletor de período no gráfico de evolução

---

### Concluído — Sprint 6C: limpeza de rotas e arquivos legados (30/06/2026)

`frontend/src/`
- `HistoricoPage.tsx` removido (stub sem conteúdo real)
- Rota `/carteira/historico` removida do router
- `Login.tsx` e `Register.tsx` duplicados de `auth/` removidos
- `Landing.tsx` restaurado com rota pública `/` em `main.tsx`
- `App.tsx` mantido como legado sem re-export que quebrava o build

---

### Adicionado — Sync semanal de dividendos de FIIs via provedor de dados (30/06/2026) — Sprint 5F

> Pipeline completo de sincronização de proventos de FIIs com job automático semanal e trigger manual via painel admin.

**`backend/app/core/config.py` + `backend/app/core/settings.py`**
- Novas variáveis de configuração: `FII_DIVIDEND_CHUNK_SIZE` (padrão 20), `FII_DIVIDEND_MAX_RETRIES` (padrão 3), `FII_DIVIDEND_BOOTSTRAP_YEARS` (padrão 5)

**`backend/app/integrations/brapi_fii_dividends.py`** *(novo)*
- Client de integração para o endpoint de dividendos de FIIs do provedor de cotações
- Suporte a até 20 símbolos por chamada (limite documentado do provedor)
- Retry com backoff exponencial em erros 429/5xx (máx. 3 tentativas)
- Normalização do payload para DTO interno `FiiDividendEvent`
- Verificação antecipada de token: sem configuração → aviso no log + retorno de lista vazia

**`backend/app/models/dividends_sync_job.py`** *(novo)*
- Model `DividendsSyncJob` para rastrear estado, lock distribuído e cursor incremental
- Campos: `locked_by` (hostname), `locked_at`, `last_cursor_date`, `started_at`, `finished_at`, `error_message`
- Métricas por execução: `assets_processed`, `events_created`, `events_updated`, `errors_count`
- Registrado em `models/__init__.py`

**`backend/alembic/versions/012_add_dividends_sync_job.py`** *(novo)*
- Migration Alembic versionada — cria tabela `dividends_sync_jobs`
- Segue padrão das migrations existentes (`009_add_fx_rates_table.py`)

**`backend/app/services/dividends_sync_service.py`** *(novo)*
- Orquestrador principal: acquire lock → fetch em lote → upsert → release lock
- Upsert idempotente em `asset_dividends` via `(asset_id, ex_date, dividend_type)` — sem N+1
- Pre-load de registros existentes em memória antes do loop de inserção
- Atualização retroativa: só sobrescreve `value_per_unit` se o valor divergir da fonte
- Falha isolada por ticker: rollback parcial com `continue` — falha em um FII não aborta o job
- Modo incremental: cursor salvo com 30 dias de overlap para absorver correções retroativas
- Modo bootstrap: `force_bootstrap=True` busca 5 anos de histórico completo
- Lock distribuído com TTL de 60 minutos: previne execuções concorrentes em multi-instância

**`backend/app/scheduler.py`**
- `job_sync_fii_dividends()` registrado com `CronTrigger(day_of_week="sat", hour=6, minute=0)`
- Complementar ao `job_sync_dividends` (domingo 2h) — sem sobreposição de janela
- Contador de jobs APScheduler: 7 → **8 jobs**
- Padrão `AsyncSessionLocal()` por job (sessão isolada)

**`backend/app/routers/admin.py`**
- `GET /admin/fii-dividends/sync/status` — retorna status, lock info, cursor e métricas da última execução
- `POST /admin/fii-dividends/sync?force_bootstrap=false` — dispara sync em `BackgroundTask`; `force_bootstrap=true` para bootstrap completo
- Ambos protegidos por `require_superadmin`
- Segue padrão `_run_*_bg()` com logs de início/conclusão/falha já estabelecido no router

---

### Corrigido — Rentabilidade: dia usa snapshot anterior real; mês usa 1º do mês calendário (30/06/2026) — Sprint 5B #54

**`backend/app/services/rentabilidade_service.py`**
- `retorno_dia_pct`: substituída busca por `D-1 exato` pela função `_snapshot_before_today()`, que retorna o snapshot imediatamente anterior ao dia atual. Corrige `0.0` toda segunda-feira e pós-feriado
- `retorno_mes_pct`: substituída janela de `D-30 corridos` pelo snapshot do último dia do mês anterior (`today.replace(day=1) - 1 dia`). Garante base fixa no início do mês calendário
- Fallback realtime (`_kpis_from_realtime`) corrigido com a mesma lógica de `primeiro_dia_mes`
- Adicionado comentário docstring com histórico de fixes e justificativas de escolha

**`frontend/src/services/rentabilidadeService.ts`**
- Interface `RentabilidadeKpis` agora inclui campo `retorno_dia_pct: number`

**`frontend/src/pages/ResumePage.tsx`**
- KpiCard "Rentabilidade" reestruturado:
  - Valor principal: **Desde o início** (retorno acumulado total)
  - 3 linhas internas com separador: **Hoje / Mês / 12 m** com cores semânticas (verde/vermelho/laranja)
  - Novo componente interno `ReturnRow` para cada linha de horizonte

---

### Concluído — Distribuição Ideal: BDRs + Reflexo no Resumo (30/06/2026) — Sprint 5E #79

**`backend/app/services/class_target_service.py`**
- `BDR` adicionado a `VALID_ASSET_CLASSES` e `_TYPE_LABEL`
- `get_targets_with_current()` retorna BDR automaticamente quando há posição ou meta configurada

**`frontend/src/hooks/useClassTargets.ts`**
- Hook chama `/targets-with-current` — sem alterações necessárias

**`frontend/src/components/resume/AllocationTargetWidget.tsx`**
- Widget itera `rows` dinamicamente — BDR aparece automaticamente
- Exibido na `ResumePage` sob o gráfico de distribuição com rótulo "Alvo da Carteira"

---

### Corrigido — Modal de Lançamento: Renda Fixa sem cotas (29/06/2026)

**`frontend/src/components/AddTransactionModal.tsx`**
- Para `asset_type = RENDA_FIXA`, o campo de quantidade agora se chama **"Valor Investido"** (sem rótulo de cotas)
- Quantidade fixada em `1` automaticamente; o usuário informa apenas o valor
- Campo de preço unitário oculto para renda fixa — apenas valor total é necessário
- Labels e placeholders revisados para evitar confusão semântica com ativos de cotas

---

### Atualizado — Dependências Frontend (29/06/2026)

**`frontend/package.json`**
- `vite` 8.0.16 → **8.1.0**
- `@vitejs/plugin-react` 6.0.2 → **6.0.3**
- `autoprefixer` 10.4.20 → **10.5.2**
- `postcss` 8.4.47 → **8.5.16**
- `@tanstack/react-query` 5.59.0 → **5.101.2**

**`backend/requirements.txt`**
- `fastapi` ≥ 0.138.0 → **≥ 0.138.1** (via PR #76)

---

### Corrigido — Módulo de Rentabilidade Renda Fixa (28/06/2026)

**`backend/app/services/rentabilidade_service.py`**
- Corrigida normalização de `asset_type` para garantir comparação correta com enum `AssetType.RENDA_FIXA`
- Corrigida comparação de `OperationType` enum ao calcular custo de compra vs. resgate
- Isolamento de sessão: upsert de `fixed_income` executado em sessão própria para não corromper sessão principal
- Cache de rentabilidade invalidado automaticamente após upsert de RF/TD
- Endpoint `flush_cache` exposto para forçar recálculo manual

**`backend/app/models/fixed_income.py` / migration 015**
- Adicionado campo `daily_liquidity` (bool) à tabela `fixed_income_investments`
- Migração Alembic `015_add_daily_liquidity_fixed_income` criada e aplicada

---

### Corrigido — Evolução Patrimonial / Bug 3 (26/06/2026)

**`backend/app/routers/portfolios.py`**
- Endpoint `GET /portfolios/{portfolio_id}/patrimonio-history` agora detecta ausência de snapshots e dispara `backfill_snapshots` em background
- Adicionado fallback on-the-fly para retornar a série histórica imediatamente, sem depender do backfill terminar

**`backend/app/services/portfolio_class_evolution_service.py`**
- Corrigida comparação de `asset_type` com conversão explícita string → enum `AssetType`
- Adicionado fallback por `Transaction.asset_type` quando o join com `assets` não encontra ticker correspondente

---

### Adicionado — Dashboard Principal e Rentabilidade (26/06/2026)

**`frontend/src/pages/ResumePage.tsx`**
- KpiCards migrados de `usePortfolioSummary` para `useRentabilidadeKpis`
- 4 cards: Patrimônio Total, Resultado Total, Proventos 12m e Rentabilidade
- Página enxuta: KPIs + evolução patrimonial + distribuição + tabela de posições

**`frontend/src/components/charts/RentabilidadeChart.tsx`**
- Gráfico de rentabilidade % mês a mês com benchmark
- Filtro de período e toggles independentes

---

### Corrigido — CSS/UI Design System (25/06/2026)

**`frontend/src/styles/globals.css`**
- Adicionadas classes `.table-dense`, `.badge`, `.badge-primary`, `.page-container`, `.page-header`, `.page-title`, `.page-subtitle`, `.input-xs`, `.text-muted`

---

### Adicionado — Página de Rentabilidade (25/06/2026)

**Backend**
- `rentabilidade_service.py`: KPIs, visão por ativo e por classe, com cache Redis TTL 5min
- `routers/rentabilidade.py`: 3 endpoints REST
- `test_rentabilidade_service.py`: 13 casos de teste

**Frontend**
- `rentabilidadeService.ts` + `useRentabilidade.ts` + `RentabilidadePage.tsx`
- UI com 8 KPIs, barra por classe e tabela por ativo

---

### Adicionado (anterior)
- `asset_seed_service.py`: popula tabela `assets` com UPSERT
- `POST /api/v1/admin/assets/seed`: endpoint superadmin + background task
- Job semanal automático para seed incremental
- Backfill histórico de preços com ordenação por prioridade de tipo
- Aba **BDR** no modal de transações do frontend

---

## [0.15.0] — 2026-06-15

### Adicionado
- Módulo de metas financeiras (`goals`)
- Módulo IRPF
- Módulo de análise de carteira (`analysis`)
- Módulo de renda fixa (`fixed_income`)
- Módulo de cotações em tempo real (`quotes`)
- Módulo de preços históricos (`prices`)
- Módulo Tesouro Direto (`treasury`)
- Módulo de câmbio (`fx`)
- Módulo de class targets (`class_targets`)
- Scheduler APScheduler com 7 jobs
- Rate limiter global via SlowAPI
- Cache Redis com TTL configurável por endpoint
- Suporte a ativos internacionais

### Alterado
- Autenticação migrada para JWT com refresh token rotativo
- Senhas com bcrypt v5

### Corrigido
- `price_history_service`: race condition em upsert paralelo
- `dividend_backfill_service`: duplicatas em re-execução

---

## [0.10.0] — 2026-05-01

### Adicionado
- Estrutura base do projeto: FastAPI + SQLAlchemy async + Alembic + PostgreSQL + Redis
- Docker Compose com backend, postgres, redis, nginx
- Módulos core: auth, users, portfolios, transactions, positions, dividends, proventos, performance
- Seed automático do superadmin no entrypoint
- Configuração de CORS, middleware de logging, handler global de exceções
- Integrações com serviços de dados de mercado (cotações, histórico, Tesouro Direto, ativos internacionais)
- Modelos: `Asset`, `AssetPrice`, `AssetDividend`
- Migrations Alembic versionadas

---

## [0.1.0] — 2026-04-01

### Adicionado
- Repositório criado, estrutura de pastas definida
- README e documentação inicial
- Decisão de arquitetura: monorepo com `backend/` e `frontend/`
