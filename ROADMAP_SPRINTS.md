# Roadmap de Desenvolvimento - SIG v2

Este documento organiza a evolucao do SIG v2 em sprints praticos. A ordem prioriza primeiro estabilizar a base tecnica, depois consolidar o nucleo financeiro e, por fim, expandir os modulos de produto.

## Visao Geral

O projeto ja possui uma base relevante: backend FastAPI, frontend React/Vite, Docker, autenticacao, carteiras, transacoes, resumo patrimonial, cotacoes e alguns modulos iniciados. O principal desafio atual e alinhar contratos entre backend/frontend e remover partes legadas que ficaram incompativeis com a versao atual do modelo de dados.

---

## Sprint 0 - Estabilizacao Inicial ✅ CONCLUIDA

**Objetivo:** fazer o sistema rodar de ponta a ponta sem quebras estruturais.

**Criterios de aceite atendidos:**
- Rotas sem prefixo duplicado `/api/v1/api/v1/...`
- Frontend sem chamadas duplicadas de prefixo
- Login e navegacao protegida funcionam
- `GET /health` responde
- Backend inicia; frontend compila

---

## Sprint 1 - Unificacao de Autenticacao e Frontend ✅ CONCLUIDA

**Objetivo:** eliminar duplicidade entre arquitetura antiga e ativa do frontend.

**Criterios de aceite atendidos:**
- Autenticacao unificada em Zustand (`useAuthStore`)
- `AuthContext` legado removido
- Logout limpa estado e redireciona
- Configuracoes exibe usuario logado sem erro

---

## Sprint 2 - Modelo de Transacoes e Servicos Legados ✅ CONCLUIDA

**Objetivo:** alinhar todos os servicos com o modelo atual de transacoes.

**Commits:** `c1434e56`, `18fbf392`, `4a4908e7`

---

## Sprint 3 - Padronizacao Async no Backend ✅ CONCLUIDA

**Objetivo:** evitar erros de runtime causados por mistura de `AsyncSession` e `Session`.

**Commits:** `297b7e8b`, `07b89607`

---

## Sprint 4 - Carteiras, Posicoes e Patrimonio ✅ CONCLUIDA — 15 Jun 2026

**Objetivo:** consolidar o nucleo patrimonial como fonte confiavel do sistema.

**Commits:** `a73d9bd7`, `38bed9b3`, `680b489f`, `cc70de49`

---

## Sprint 5 - Cotacoes e Integracoes de Mercado ✅ CONCLUIDA — 15 Jun 2026

**Objetivo:** tornar cotacoes mais robustas e previsiveis; implementar historico patrimonial real via snapshots diarios.

**Escopo executado:**
- Pipeline de cotacoes 3 camadas: `asset_types.py`, `Asset.last_price` (migration 004), `quotes_service.py`
- BRAPI refatorado: bulk, single, historical
- `price_history_service.py`: OHLCV diario no banco
- `PortfolioSnapshot` model + migration 005
- `portfolio_snapshot_service.py`: backfill, refresh, get_daily_evolution, get_monthly_evolution
- `performance_service.py`: historico com valor de mercado real
- `scheduler.py`: 6 jobs, job 19h00 = update_all_quotes + refresh_today_snapshot
- `routers/performance.py`: endpoints `/evolution/daily`, `/evolution/monthly`, `/evolution/backfill`

**Criterios de aceite atendidos:**
- ✅ Falha em BRAPI/yfinance nao derruba endpoints de posicoes
- ✅ Cotacoes ausentes retornam `None`
- ✅ Historico patrimonial com valor de mercado real
- ✅ Scheduler orquestrado com ordem correta

**Commits:** `bb258df8`, `14f4b50e`, `315325e9`, `9ea72604`, `9015538d`, `c335b513`, `b4573326`, `4a8fbda6`, `c8a57e83`, `f3a91f74`, `239bcd92`

---

## Sprint 6 - Proventos ✅ CONCLUIDA — 15 Jun 2026

**Objetivo:** entregar proventos confiaveis de ponta a ponta: backend com backfill correto e 4 endpoints + frontend conectado com filtros, historico mensal e sincronizacao manual.

**Escopo executado:**

### Backend
- `dividend_backfill_service.py`: `_net_qty_on_date` e `_portfolios_with_ticker` corrigidos para usar `ticker`
- `proventos_service.py`: reescrito em AsyncSession — 4 funcoes
- `routers/proventos.py`: reescrito em async — 4 endpoints funcionais
- `routers/dividends.py`: novo `POST /dividends/sync` — sincronizacao manual, 202 Accepted

### Frontend
- `proventosService.ts`: tipos e URLs alinhados; `sync()` adicionado
- `useProventos.ts`: hooks alinhados; `useSyncProventos` adicionado
- `ProventosPage.tsx`: KPIs corretos, toggle, botao sync, lista paginada

**Criterios de aceite atendidos:**
- ✅ Proventos exibem valor por unidade e valor total
- ✅ Recebidos e futuros separados por status
- ✅ Backfill correto: quantity calculada na data-ex pelo ticker
- ✅ Sincronizacao idempotente
- ✅ Frontend conectado e compilando

**Commits backend:** `73538f57`, `75790b79`, `ff41314a`, `d2e7b5d5`
**Commits frontend:** `c8ed7f85`, `a6b7ffef`, `670fc7bb`

---

## [Manutencao] - 15 Jun 2026 (pos-sprint) ✅ CONCLUIDA

**Executado:**
- PRs #2 e #3 fechados (obsoletos)
- PR #4 mergeado — GitHub Actions atualizados
- `frontend/Dockerfile` corrigido — fallback `npm install`
- `frontend/package-lock.json` adicionado
- `routers/auth.py` e `routers/portfolios.py` — imports corrigidos
- `reset_pwd.py` removido

**Pendente (seguranca):** historico do git ainda contem `reset_pwd.py` com senha `Admin@123` no commit `8d7a99a9`. Executar `git filter-repo` e trocar a senha nos ambientes.

---

## [Hotfix] - 18 Jun 2026 ✅ CONCLUIDO

### Tabela de Ativos (PositionTable) — 3 bugs corrigidos

**Problemas corrigidos:**
- Cards duplicados no desktop (Tailwind `md:hidden` sem breakpoints configurados)
- Coluna "P. Atual" sempre `—` (comportamento correto revelado; L1 vazio deixa visivel)
- Coluna "Valor Atual" repetindo o valor investido (`enrich_with_prices` usava `total_invested` como fallback)

**Arquivos alterados:**
- `frontend/src/components/resume/PositionTable.tsx` — commit `f82c6dc3`
- `backend/app/services/portfolio_service.py` — commit `25754acb`
- `backend/app/schemas/position.py` — commit `25754acb`

---

## [Security Hotfix] - 21 Jun 2026 ✅ CONCLUIDO

- `pydantic-settings` atualizado `2.14.1` → `2.14.2` (GHSA-4xgf-cpjx-pc3j) — PR #25 mergeado

---

## Sprint 7 - Rentabilidade ✅ CONCLUIDA — 22 Jun 2026

**Objetivo:** calcular rentabilidade de forma util e confiavel para decisao do usuario.

### Itens concluidos

| # | Item | Status | Commits |
|---|---|---|---|
| 1 | L1 vazio — `_db_set` sem commit fora do scheduler | ✅ | `f18a0a8` |
| 2 | `sum_dividends` ignorava proventos manuais (LEFT JOIN) | ✅ | `18ddf58` |
| 3 | `rentabilidade_pct` ausente em `AssetGroupOut` | ✅ | `8e05e0d` |
| 4 | Dupla formatacao de percentual em `ResumePage.tsx` | ✅ | `ec36720` |
| 5 | Logica de rentabilidade por ativo | ✅ | existente em `portfolio_service.py` |
| 6 | `total_gain` / `total_gain_pct` no `PortfolioSummary` | ✅ | existente em `portfolio_service.py` |
| 7 | Lucro realizado via `proventos_em_carteira` | ✅ | existente em `portfolio_service.py` |
| 8 | Proventos contribuindo para `rentabilidade_total` | ✅ | existente em `portfolio_service.py` |
| A2 | Paginacao server-side em `GET /transactions` | ✅ | `a00a1aa` (back) `27d0f7b` (front) |

### Campos de rentabilidade do summary (referencia)

| Campo backend | Alias frontend | Significado |
|---|---|---|
| `total_patrimonio` / `current_value` | `patrimonio` | Valor atual da carteira |
| `total_investido` / `total_invested` | `investido` | Custo total das posicoes abertas |
| `variacao_valor` / `total_gain` | `variacaoVal` | Ganho bruto de capital (R$) |
| `variacao_percentual` / `total_gain_pct` | `variacaoPct` | Variacao percentual do capital |
| `lucro_total` | `lucroTotal` | Capital + proventos ativos em carteira |
| `rentabilidade_total` | `rentabilidade` | `lucro_total / total_invested * 100` |
| `dividendos_recebidos_12m` | `dividendos12m` | Proventos recebidos nos ultimos 12 meses |
| `total_proventos` | `totalProv` | Total historico de proventos |
| `ganho_capital` | `ganhoCapital` | Alias de `total_gain` (para KpiCard) |

**Criterios de aceite atendidos:**
- ✅ Cotacoes aparecem para ativos nacionais com L1 ou L3
- ✅ `current_price` e `current_value` preenchidos
- ✅ Rentabilidade por ativo bate com transacoes e cotacoes
- ✅ Carteira mostra retorno total com e sem proventos
- ✅ KPIs "Resultado" e "Variacao" mostram valores coerentes
- ✅ Tela nao quebra quando cotacao esta ausente

---

## Sprint 11 - Metas e Alocacao (Distribuicao da Carteira) ✅ CONCLUIDA — 22 Jun 2026

**Objetivo:** permitir que o usuario defina metas percentuais por classe de ativo diretamente em Configuracoes.

### Escopo executado

**Novos arquivos:**
- `frontend/src/services/classTargetsService.ts` — `list`, `upsert`, `remove` via `GET/PUT/DELETE /portfolios/{id}/class-targets`
- `frontend/src/hooks/useClassTargets.ts` — `useClassTargets`, `useUpsertClassTarget`, `useDeleteClassTarget`
- `frontend/src/components/configuracoes/DistribuicaoCarteira.tsx` — componente completo com edicao inline, badge de total, select filtrado, delete individual

**Arquivos alterados:**
- `frontend/src/pages/Configuracoes.tsx` — migrado de SectionCards empilhados para 4 abas: **Conta / Carteiras / Distribuicao / Avancado**

**Commits:**
- `ccded3a` — classTargetsService.ts + useClassTargets.ts + DistribuicaoCarteira.tsx
- `703d047` — Configuracoes.tsx migrado para abas

**Criterios de aceite atendidos:**
- ✅ Aba "Distribuicao" aparece em Configuracoes e carrega metas do backend
- ✅ Edicao inline com salvar individual por classe (dirty state)
- ✅ Badge de total com cor dinamica (verde = 100%, laranja < 100%, vermelho > 100%)
- ✅ Select de nova classe filtrado (exclui ja configuradas)
- ✅ Delete individual chama `DELETE` imediatamente
- ✅ Estado vazio com mensagem descritiva
- ✅ Pagina Configuracoes em 4 abas organizadas
- ✅ Frontend compila sem erros TypeScript

---

## [Sprint 7.5] - Hardening de Seguranca e Qualidade do Backend ✅ CONCLUIDA (parcial) — 22 Jun 2026

**Objetivo:** fechar os gaps criticos e de alta prioridade identificados na analise de 21 Jun 2026.

### Itens CRITICOS

| # | Item | Status | Commits |
|---|---|---|---|
| C1 | Traceback exposto em producao (`main.py`) | ✅ | `*` |
| C2 | `debug.py` sem audit log e rate limiting | ✅ | `59ba7ff` |
| C3 | Refresh token sem blacklist / revogacao | ✅ | `9ff0e40` + `c9e5b96` + `71084de` |

### Itens de ALTA PRIORIDADE

| # | Item | Status | Commits |
|---|---|---|---|
| A1 | Rate limiting no endpoint de login | ⏳ Pendente | — |
| A2 | Paginacao server-side em `GET /transactions` | ✅ Concluido na Sprint 7 | `a00a1aa` + `27d0f7b` |
| A3 | Routers stub ativos sem implementacao | ⏳ Pendente | — |
| A4 | Consolidar `quote_service.py` e `quotes_service.py` | ⏳ Pendente | — |

### Itens de MEDIA PRIORIDADE

| # | Item | Status |
|---|---|---|
| M1 | Health check real (SELECT 1 + Redis ping) | ⏳ Pendente |
| M2 | Scheduler com isolamento de falha por job | ⏳ Pendente |
| M3 | Cache no `performance_service.py` (TTL 5min Redis) | ⏳ Pendente |
| M4 | Timeout no `logo_service.py` | ⏳ Pendente |

### [Bugfixes] - 22 Jun 2026 (mesma sessao)

| # | Bug | Status | Commit |
|---|---|---|---|
| B1 | Modal desktop: abas com `flexWrap` para exibir Renda Fixa e Cripto | ✅ | `ffeb622` |
| B2 | PositionTable: Stocks/ETF INT exibiam preco em R$ sem conversao | ✅ | `2b5542b` |
| B3 | Transacoes.tsx: preco/total em R$ para ativos USD | ✅ | `2b5542b` |

---

## Sprint 8 - Historico Patrimonial (frontend)

**Objetivo:** integrar endpoints de evolucao no frontend.

> **Nota:** infraestrutura de snapshots foi antecipada na Sprint 5.

**Escopo:**
- Integrar `GET /evolution/daily` e `GET /evolution/monthly` no frontend
- Graficos de linha (diario) e barras (mensal)
- Seletores de periodo: 6m, 12m, 24m, tudo
- Comparativo: valor investido vs valor de mercado

**Prioridade:** media.

---

## Sprint 9 - Patrimonio por Classe

**Objetivo:** transformar a area de patrimonio em modulo completo.

**Criterios de aceite:**
- Renda variavel lista ativos corretamente
- Tesouro Direto lista titulos
- Renda fixa tem fluxo minimo planejado ou implementado

**Prioridade:** media.

---

## Sprint 10 - Renda Fixa e Tesouro Direto

**Objetivo:** dar suporte real a ativos de renda fixa.

**Escopo:**
- CDB, LCI, LCA, CRI, CRA, debenture, poupanca
- Indexadores: CDI, IPCA+, Selic, prefixado, IGPM+
- Tesouro Direto com vencimento, quantidade, preco de compra e atual
- Marcacao a mercado

**Prioridade:** media.

---

## Sprint 12 - IRPF ⚠️ BACKEND + FRONTEND BASICO JA IMPLEMENTADOS

**Objetivo:** revisar, testar e completar o modulo de IRPF ja existente.

> **Situacao atual (22 Jun 2026 — auditoria):**
> - `irpf_service.py` (24 KB) — implementado
> - `routers/irpf.py` (5.6 KB) — implementado
> - `IRPFPage.tsx` (23.6 KB) — implementado
> - Status documentado anteriormente como Sprint futura estava incorreto

**Escopo real da Sprint 12 (revisao e completude):**
- Auditar cobertura do `irpf_service.py`: posicao em 31/12, Bens e Direitos, rendimentos isentos, JCP, tributaveis
- Verificar calculo de lucro/prejuizo realizado por mes (Preco Medio Ponderado)
- Validar `IRPFPage.tsx`: exportacao de relatorio anual, alinhamento de campos com backend
- Adicionar testes para os calculos criticos de IR
- Documentar o fluxo de geracao do relatorio

**Prioridade:** media.

---

## Sprint 13 - Analise da Carteira

**Objetivo:** entregar diagnosticos e insights sobre a carteira.

**Prioridade:** media-baixa.

---

## Sprint 14 - Administracao e Operacao

**Objetivo:** melhorar gestao e manutencao do sistema.

**Prioridade:** media.

---

## Sprint 15 - Qualidade, CI e Release

**Objetivo:** deixar o projeto pronto para evolucao continua.

**Prioridade:** alta apos estabilizacao inicial.

---

## Backlog Futuro

- Importacao de notas de corretagem
- Importacao via extratos B3
- Integracao com corretoras
- Alertas por e-mail ou notificacao
- Multi-moeda com cambio historico completo
- Exportacao para Excel
- Dashboard comparando carteira com CDI, IPCA, Ibovespa e S&P 500
- Rebalanceamento automatico sugerido
- App mobile ou PWA refinado

---

## Ordem de Execucao

| Sprint | Status |
|---|---|
| Sprint 0 — Estabilizacao Inicial | ✅ Concluida |
| Sprint 1 — Autenticacao e Frontend | ✅ Concluida |
| Sprint 2 — Modelo de Transacoes | ✅ Concluida |
| Sprint 3 — Padronizacao Async | ✅ Concluida |
| Sprint 4 — Carteiras, Posicoes e Patrimonio | ✅ Concluida — 15 Jun 2026 |
| Sprint 5 — Cotacoes e Integracoes | ✅ Concluida — 15 Jun 2026 |
| Sprint 6 — Proventos (backend + frontend) | ✅ Concluida — 15 Jun 2026 |
| Manutencao pos-sprint — Infra e hotfixes | ✅ Concluida — 15 Jun 2026 |
| Hotfix — Tabela de Ativos | ✅ Concluido — 18 Jun 2026 |
| Security Hotfix — pydantic-settings CVE | ✅ Concluido — 21 Jun 2026 |
| Sprint 7 — Rentabilidade | ✅ Concluida — 22 Jun 2026 |
| Sprint 11 — Metas e Alocacao (Distribuicao) | ✅ Concluida — 22 Jun 2026 |
| Sprint 7.5 — Hardening Seguranca (C1–C3 ✅, A1/A3/A4/M1–M4 ⏳) | 🔄 Parcial — 22 Jun 2026 |
| Sprint 8 — Historico Patrimonial (frontend) | ⏳ |
| Sprint 9 — Patrimonio por Classe | ⏳ |
| Sprint 10 — Renda Fixa e Tesouro | ⏳ |
| Sprint 12 — IRPF (revisar implementacao existente) | ⏳ |
| Sprint 13 — Analise da Carteira | ⏳ |
| Sprint 14 — Administracao | ⏳ |
| Sprint 15 — Qualidade, CI e Release | ⏳ |

---

## Definicao de Pronto

Uma sprint so deve ser considerada concluida quando:

- O fluxo principal da sprint funciona no navegador ou via API.
- O backend inicia sem erros.
- O frontend compila.
- Ha pelo menos testes ou validacoes manuais documentadas para o comportamento central.
- Nao foram introduzidas rotas duplicadas, chamadas duplicadas de prefixo ou contratos divergentes.
- O README ou este roadmap foi atualizado se houver mudanca relevante de escopo.
