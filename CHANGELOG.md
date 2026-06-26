# Changelog — SGI v2

Todas as mudanças relevantes do projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Unreleased] — branch `stable-15jun`

### Adicionado — Dashboard Principal e Rentabilidade (26/06/2026)

**`frontend/src/pages/ResumePage.tsx`**
- KpiCards migrados de `usePortfolioSummary` para `useRentabilidadeKpis` — dados agora consistentes com a página de Rentabilidade
- 4 cards: Patrimônio Total, Resultado Total (com breakdown não-realizado/realizado), Proventos 12m e Rentabilidade (mês + 12m + desde início)
- Removidos `QuickNav` e seletor de carteira inline (navegação centralizada no topbar/sidebar)
- Removido `usePortfolioSummary` — sem double fetch
- Página enxuta: 4 KpiCards + evolução patrimonial + distribuição + tabela de posições

**`frontend/src/components/charts/RentabilidadeChart.tsx`** (novo)
- Gráfico de rentabilidade % mês a mês com comparativo de benchmarks
- Barras: retorno mensal da carteira via `useMonthlyEvolution` (campo `return_pct`)
- Linhas de benchmark com toggle independente:
  - **IBOV**: histórico mensal via BRAPI (`^BVSP`, intervalo `1mo`)
  - **CDI**: BCB série 4391 (CDI over acumulado no mês)
  - **IPCA**: BCB série 433 (variação mensal), desligado por padrão
- Filtro de período: 6m / 12m / 24m / todo período
- Tooltip customizado com valores de todos os séries por mês
- Nota de rodapé citando as fontes de dados

**`frontend/src/pages/RentabilidadePage.tsx`**
- `RentabilidadeChart` inserido entre os KpiCards e a tabela de ativos
- Sem alteração na estrutura existente de KpiCards, tabela por ativo e barras por classe

---

### Corrigido — CSS/UI Design System (25/06/2026)

**`frontend/src/styles/globals.css`**
- Adicionada classe utilitária `.table-dense` para tabelas compactas (th/td com padding reduzido, font-size `var(--text-xs)`, border-bottom automático)
- Adicionadas classes `.badge` e `.badge-primary` para rótulos inline (ex: badge “atual” no resumo mensal)
- Adicionados tokens de layout `.page-container`, `.page-header`, `.page-title`, `.page-subtitle` para consistência entre páginas
- Adicionada classe `.input-xs` (altura 28px, padding menor, font-size `var(--text-xs)`) para inputs compactos em cabeçalhos de grupo
- Adicionado utilitário `.text-muted` como classe Tailwind-compatível mapeada para `var(--color-text-muted)`

**`frontend/src/styles/components.css`**
- `.positions-table`: adicionado `table-layout: fixed` para que colunas respeitem larguras definidas e não causem overflow no container
- Definidas larguras padrão por tipo de coluna: Data (`5.5rem`), Tipo (`6.5rem`), Ativo (`auto — flex`)
- Adicionados `overflow: hidden` e `text-overflow: ellipsis` em `th` e `td` para conteúdo longo (tickers, valores)

**`frontend/src/pages/Transacoes.tsx`**
- Substituído wrapper raiz por `page-container` e cabeçalho por `page-header` / `page-title` / `page-subtitle`
- Card do gráfico de aportes removido `overflow-hidden` para que o tooltip do Recharts (position:absolute) não seja cortado
- Inputs de busca por grupo corrigidos para usar classe `input input-xs` (antes usavam `input-xs` sem a base `input`)
- Strings de texto inline com `style={{ color: 'var(--color-text-muted)' }}` substituídas pela classe `.text-muted`

**`frontend/src/pages/PatrimonioPage.tsx`**
- Extraído componente genérico `<ToggleGroup<T>>`: cada botão recebe `border-radius` individual nos extremos, eliminando a necessidade de `overflow-hidden` no container pai (que cortava o estado ativo)
- Toggle Diário/Mensal e seletor de Período passam a usar `<ToggleGroup>` em vez de `<div className="overflow-hidden">`
- Card do gráfico de evolução removido `overflow-hidden` (tooltip Recharts)
- Tabela “Resumo Mensal” migrada para classe `.table-dense`
- Coluna Rentabilidade da tabela mensal exibe ícone `TrendingUp` (verde) ou `TrendingDown` (vermelho) ao lado do valor percentual
- Badge “atual” usa classes `.badge .badge-primary` em vez de estilo inline
- Importado `TrendingDown` do `lucide-react`

---

### Corrigido — Tesouro Direto & Cripto (25/06/2026)

**Backend — `brapi.py`**
- `fetch_treasury_indicators`: adicionada **3ª tentativa de fallback** via `api.radaropcoes.com` quando BRAPI falha completamente
- `fetch_treasury_indicators`: token inválido/expirado (`400/401/403`) agora loga o status code explicitamente e cai no fallback `/list` sem lançar exceção
- Fluxo agora tem **3 camadas em cascata**: `/v2/treasury/indicators` → `/v2/treasury/list` → `api.radaropcoes.com`

**Backend — `tesouro_nacional.py`**
- Headers anti-403 adicionados (`User-Agent`, `Accept`, `Referer`)
- Fallback adicional para endpoint `tesourotransparente.tesouro.gov.br` quando a API primária falha

**Backend — `rentabilidade_service.py`**
- `_proventos_total`: corrigido para usar `Dividend.total_value` (campo correto do modelo) em vez de `Dividend.amount`

**Backend — serviços de cotação**
- `quotes_service.py`: passa a usar `fetch_treasury_prices` com as 3 camadas de resolução de slug para Tesouro Direto
- `_normalize_crypto_ticker`: adicionado mapa `_CRYPTO_NAME_MAP` cobrindo 35 criptomoedas por nome completo

### Adicionado — Página de Rentabilidade (25/06/2026)

**Backend**
- `rentabilidade_service.py`: serviço de agregação com 3 funções, cache Redis TTL 5min
- `routers/rentabilidade.py`: 3 endpoints REST com verificação de ownership por carteira:
  - `GET /api/v1/portfolios/{id}/rentabilidade/kpis`
  - `GET /api/v1/portfolios/{id}/rentabilidade/ativos`
  - `GET /api/v1/portfolios/{id}/rentabilidade/classes`
- 13 testes em `test_rentabilidade_service.py` com SQLite in-memory + mocks

**Frontend**
- `rentabilidadeService.ts` + `useRentabilidade.ts` + `RentabilidadePage.tsx`
- UI: 8 KpiCards, barra por classe, tabela por ativo com filtros

### Adicionado (anterior)
- `asset_seed_service.py`: popula tabela `assets` via BRAPI com UPSERT por `(ticker, asset_type)`
- `POST /api/v1/admin/assets/seed`: endpoint superadmin + background task
- Job semanal automático (segunda às 03h) para seed incremental
- Backfill histórico de preços com ordenação por prioridade de tipo
- Aba **BDR** no modal de transações do frontend

### Corrigido (anterior)
- Boot sequence sem Etapa 3 redundante de proventos
- `ImportError upsert_daily_prices` removido de `asset_onboarding_service`
- Background task do seed com log de início + traceback completo

---

## [0.15.0] — 2026-06-15

### Adicionado
- Módulo de metas financeiras (`goals`): CRUD completo com progresso calculado automaticamente
- Módulo IRPF: cálculo de imposto sobre ganho de capital por operações de renda variável
- Módulo de análise de carteira (`analysis`): score de diversificação, concentração por setor e sugestões
- Módulo de renda fixa (`fixed_income`): cadastro e acompanhamento de CDB, LCI, LCA, Debentures
- Módulo de cotações em tempo real (`quotes`): endpoint consolidado com cache Redis (TTL 15min)
- Módulo de preços históricos (`prices`): histórico OHLCV com fallback BRAPI → Alpha Vantage → yfinance
- Módulo Tesouro Direto (`treasury`): cadastro de títulos com cotação via BRAPI v2
- Módulo de câmbio (`fx`): cotação e histórico de pares cambiais via BRAPI v2/currency
- Módulo de class targets (`class_targets`): definição de alocação alvo por classe de ativo por carteira
- Scheduler APScheduler com 7 jobs: atualização de preços, proventos, câmbio, seed de ativos
- Rate limiter global via SlowAPI + middleware
- Cache Redis com TTL configurável por endpoint
- Integração Alpha Vantage com rate limiter dedicado (4 req/min via TokenBucket)
- Health check real com verificação de conectividade PostgreSQL e Redis
- Suporte a ativos internacionais (BDR, ETF_INTL, STOCK_INTL) via yfinance + Alpha Vantage

### Alterado
- Autenticação migrada para JWT com refresh token rotativo
- Senhas com bcrypt v5 (rounds configurável)
- Modelos de banco com soft-delete e timestamps automáticos

### Corrigido
- `price_history_service`: race condition em upsert de preços paralelos
- `dividend_backfill_service`: duplicatas em re-execução corrigidas com `ON CONFLICT DO NOTHING`

---

## [0.10.0] — 2026-05-01

### Adicionado
- Estrutura base do projeto: FastAPI + SQLAlchemy async + Alembic + PostgreSQL + Redis
- Docker Compose com serviços: backend, postgres, redis, nginx
- Módulos core: auth, users, portfolios, transactions, positions, dividends, proventos, performance
- Seed automático do superadmin no entrypoint
- Configuração de CORS, middleware de logging, handler global de exceções
- Integração BRAPI: cotações, histórico de preços, dados de ativos, Tesouro Direto
- Integração yfinance: fallback para ativos internacionais
- Modelo `Asset` com campos: ticker, name, asset_type, sector, currency, logo_url, last_price
- Modelo `AssetPrice` com constraint única `uq_price_asset_timestamp`
- Modelo `AssetDividend` para histórico de proventos
- Migrations Alembic versionadas

---

## [0.1.0] — 2026-04-01

### Adicionado
- Repositório criado, estrutura de pastas definida
- README e documentação inicial
- Decisão de arquitetura: monorepo com `backend/` e `frontend/`
