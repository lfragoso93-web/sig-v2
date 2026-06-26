# RESUME — SIG v2

Estado atual do projeto em 26 Jun 2026. Ponto de partida para a proxima sessao.

---

## Estado Geral

| Item | Status |
|---|---|
| Backend FastAPI | ✅ Rodando — async em todos os servicos |
| Frontend React/Vite | ✅ Compilando |
| Autenticacao | ✅ Zustand + JWT |
| Carteiras e Posicoes | ✅ Concluido |
| Cotacoes e Snapshots | ✅ Concluido |
| Proventos (backend) | ✅ Concluido |
| Proventos (frontend) | ✅ Concluido |
| Catalogo de Ativos (seed) | ✅ Concluido — 2.259 ativos via BRAPI |
| Rentabilidade (backend) | ✅ Concluido — 3 endpoints + testes |
| Rentabilidade (frontend) | ✅ Concluido — RentabilidadePage.tsx |
| IRPF (frontend) | ✅ Concluido — IRPFPage.tsx |
| Hotfixes Tesouro/Cripto | ✅ Concluido — 3 camadas de fallback |
| CSS Design System | ✅ Concluido — globals.css + components.css |
| Dashboard principal | 🔜 Proximo — Sprint 5 em andamento |

---

## Ultimo commit relevante

`fix(css): design system — table-dense, badge, page-container, positions-table (25/06/2026)`

---

## Sprint 5 — O que ja foi concluido

| Entrega | Data |
|---|---|
| `rentabilidade_service.py` — KPIs, por ativo e por classe (cache Redis TTL 5min) | 25/06/2026 |
| `routers/rentabilidade.py` — 3 endpoints com ownership check | 25/06/2026 |
| `test_rentabilidade_service.py` — 13 casos SQLite in-memory | 25/06/2026 |
| `RentabilidadePage.tsx` — 8 KpiCards, tabela por ativo, filtros | 25/06/2026 |
| Hotfix `fetch_treasury_indicators` — 3 camadas de fallback (BRAPI → /list → radaropcoes) | 25/06/2026 |
| Hotfix `_normalize_crypto_ticker` — mapa de 35 nomes completos | 25/06/2026 |
| `globals.css` — `.table-dense`, `.badge`, `.page-container/header/title`, `.input-xs`, `.text-muted` | 25/06/2026 |
| `components.css` — `.positions-table` com `table-layout: fixed` | 25/06/2026 |
| `Transacoes.tsx` e `PatrimonioPage.tsx` — migracao para design system | 25/06/2026 |

---

## Sprint 5 — Pendencias (proximos passos)

- [ ] Dashboard principal com resumo de patrimônio
- [ ] Grafico de evolucao patrimonial (linha historica)
- [ ] Distribuicao por classe de ativo (pizza/donut)
- [ ] Lista de posicoes com rentabilidade individual
- [ ] Tela de metas financeiras (`MetasPage.tsx` — stub vazio, backend existe)
- [ ] Tela de renda fixa (`fixed_income` — backend existe, frontend pendente)
- [ ] `GET /api/v1/assets` — listagem paginada com filtros (backend `assets.py` existe, frontend pendente)
- [ ] `GET /api/v1/assets/{ticker}` — detalhe do ativo com cotacao atual
- [ ] Tela de listagem de ativos no frontend
- [ ] Investigar e corrigir `YFRateLimitError` para ativos internacionais (IVV, NVDA, INTR, TFLO)

---

## Endpoints de Rentabilidade

| Endpoint | Descricao |
|---|---|
| `GET /portfolios/{id}/rentabilidade/kpis` | 13 campos: patrimonio, custo, aportado, ganhos, retorno total/mes/12m/desde inicio, proventos |
| `GET /portfolios/{id}/rentabilidade/ativos` | Por ativo: qty, avg_price, current_value, unrealized/realized/total PnL, is_open |
| `GET /portfolios/{id}/rentabilidade/classes` | Agrupado por ACAO/FII/ETF com alocacao_pct e total_pnl_pct |

---

## Endpoints de Proventos (referencia)

| Endpoint | Descricao |
|---|---|
| `GET /portfolios/{id}/proventos/summary` | KPIs: total_recebido, total_a_receber, total_12m, media_mensal_12m |
| `GET /portfolios/{id}/proventos` | Lista paginada (filtros: status, year, asset_type) |
| `GET /portfolios/{id}/proventos/historico-mensal` | Grid por ano/mes |
| `GET /portfolios/{id}/proventos/distribuicao` | Distribuicao % por ativo |
| `POST /portfolios/{id}/dividends/sync` | Sincronizacao manual — 202 Accepted |

---

## Pendencias tecnicas conhecidas

- `ProventosHistoricoTable.tsx` usa classes CSS legadas (`text-muted`, `border-light-border`) — a migrar para CSS vars
- `ProventosDonutChart` precisa de validacao com dados reais de distribuicao
- `YFRateLimitError` afeta ativos internacionais (IVV, NVDA, INTR, TFLO) — sem solucao ainda
- `MetasPage.tsx` e `AnalisePage.tsx` sao stubs vazios (< 200 bytes) — backend existe, frontend pendente
- Nenhum teste automatizado escrito para o frontend ainda

---

## Paginas do Frontend (estado atual)

| Pagina | Arquivo | Status |
|---|---|---|
| Login / Register | `Login.tsx`, `Register.tsx` | ✅ |
| Landing / Welcome | `Landing.tsx`, `WelcomePage.tsx` | ✅ |
| Patrimonio | `PatrimonioPage.tsx` | ✅ |
| Transacoes | `Transacoes.tsx` | ✅ |
| Proventos | `ProventosPage.tsx` | ✅ |
| Rentabilidade | `RentabilidadePage.tsx` | ✅ |
| IRPF | `IRPFPage.tsx` | ✅ |
| Lancamentos | `LancamentosPage.tsx` | ✅ |
| Configuracoes | `Configuracoes.tsx` | ✅ |
| Resumo/Dashboard | `ResumePage.tsx` | 🔧 Parcial |
| Metas | `MetasPage.tsx` | 🔜 Stub |
| Analise | `AnalisePage.tsx` | 🔜 Stub |
| Historico | `HistoricoPage.tsx` | 🔜 Stub |

---

## Decisoes de arquitetura consolidadas

- **AsyncSession** em todos os servicos e routers do backend
- **Dois niveis de provento:** `asset_dividends` (global) + `dividends` (carteira)
- **SKIP_TYPES:** CRIPTO, TESOURO_DIRETO, RENDA_FIXA ignorados no backfill
- **Calculo de quantity:** posicao liquida na data-ex via `Transaction(portfolio_id, ticker, date <= ex_date)`
- **net_value:** `total_value * 0.85` para JCP; `total_value` para os demais
- **Prefixo de rotas:** gerenciado pelo `main.py` — nao hardcodar `/api/v1` nos routers
- **Tipos de ativo:** fonte unica em `asset_types.py`
- **Cache Redis:** TTL 5min para rentabilidade, 15min para cotacoes
- **Crypto tickers:** normalizados via `_CRYPTO_NAME_MAP` (35 entradas) — ex: BITCOIN → BTC
- **Tesouro Direto:** 3 camadas de fallback — BRAPI /indicators → /list → radaropcoes
- **Asset seed:** UPSERT idempotente por `(ticker, asset_type)`, job semanal toda segunda as 03h
