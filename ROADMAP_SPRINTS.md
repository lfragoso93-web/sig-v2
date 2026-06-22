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

**Ponto de atencao aberto:** `quotes_service` pode estar com L1 vazio por nao encontrar `Asset` com o mesmo `asset_type` que vem das transacoes. Investigar na Sprint 7.

---

## [Security Hotfix] - 21 Jun 2026 ✅ CONCLUIDO

- `pydantic-settings` atualizado `2.14.1` → `2.14.2` (GHSA-4xgf-cpjx-pc3j) — PR #25 mergeado

---

## Sprint 7 - Rentabilidade 🔄 EM ANDAMENTO — iniciada 22 Jun 2026

**Objetivo:** calcular rentabilidade de forma util e confiavel para decisao do usuario.

### Progresso (22 Jun 2026)

| # | Item | Status | Commits |
|---|---|---|---|
| 1 | L1 vazio — `_db_set` sem commit fora do scheduler | ✅ Corrigido | `f18a0a8` |
| 2 | `sum_dividends` ignorava proventos manuais (LEFT JOIN) | ✅ Corrigido | `18ddf58` |
| 3 | `rentabilidade_pct` ausente em `AssetGroupOut` | ✅ Corrigido | `8e05e0d` |
| 4 | Dupla formatacao de percentual em `ResumePage.tsx` | ✅ Corrigido | `ec36720` |
| 5 | Logica de rentabilidade por ativo | 🔜 Pendente | — |
| 6 | `total_gain` / `total_gain_pct` no `PortfolioSummary` | 🔜 Pendente | — |
| 7 | Lucro realizado (ativos vendidos) contabilizado | 🔜 Pendente | — |
| 8 | Proventos contribuindo para rentabilidade total | 🔜 Pendente | — |

### Arquivos ja revisados

| Arquivo | Status |
|---|---|
| `backend/app/services/quotes_service.py` | ✅ Revisado e corrigido (L1) |
| `backend/app/models/asset.py` | ✅ Revisado — `asset_type` e String; `last_price` populado via savepoint |
| `backend/app/core/asset_types.py` | ✅ Revisado — sem inconsistencias |

### Arquivos para revisar (pendentes)

| Arquivo | O que verificar |
|---|---|
| `backend/app/services/portfolio_service.py` | `enrich_with_prices`, `get_portfolio_summary`, calculo de `variation_value`/`variation_percent` |
| `backend/app/routers/positions.py` | Fluxo completo de `refresh=True` — testa se `update_quotes_for_portfolio` resolve L1 |
| `frontend/src/pages/ResumePage.tsx` | KPI cards de Resultado, Variacao, Rentabilidade — alinhar com campos reais do backend |

**Criterios de aceite (Sprint 7):**
- Cotacoes aparecem para ativos nacionais (ACAO, FII, ETF) com L1 ou L3
- `current_price` e `current_value` preenchidos na tabela de ativos
- Rentabilidade por ativo bate com transacoes e cotacoes
- Carteira mostra retorno total com e sem proventos
- Ativos vendidos continuam contribuindo para lucro realizado
- Tela nao quebra quando cotacao esta ausente
- KPI "Resultado" e "Variacao" mostram valores coerentes

**Prioridade:** alta.

---

## [Sprint 7.5] - Hardening de Seguranca e Qualidade do Backend — iniciar apos Sprint 7

**Objetivo:** fechar os gaps criticos e de alta prioridade identificados na analise de 21 Jun 2026, antes de seguir com novas funcionalidades.

> Esta sprint entra entre Sprint 7 e Sprint 8 por conter itens criticos que nao devem aguardar.

### Itens CRITICOS (executar primeiro)

**C1 — Traceback exposto em producao (`main.py`)**
- O `global_exception_handler` retorna stack trace completo na resposta JSON
- Correcao: logar internamente via `logging.error` e retornar apenas mensagem generica ao cliente
- Diferenciar ambiente: traceback visivel apenas em `DEBUG=true`

**C2 — Router `debug.py` sem controle de ciclo de vida**
- Endpoints de reset de senha e criacao de usuario com qualquer role estao ativos sempre que `ADMIN_SECRET` existir
- Correcao: adicionar audit log de acesso, rate limiting (max 5 req/min), e documentar processo de desativacao
- Avaliar migrar funcionalidade para painel admin autenticado

**C3 — Refresh token sem blacklist / revogacao**
- Logout nao invalida o refresh token; token permanece valido ate expirar (7 dias)
- Correcao: criar tabela `revoked_tokens` no banco (ou usar Redis) e checar em `decode_token`
- Garantir que logout chame endpoint de revogacao

### Itens de ALTA PRIORIDADE

**A1 — Rate limiting no endpoint de login**
- `POST /auth/login` sem throttling permite brute force ilimitado
- Correcao: adicionar `slowapi` ou middleware de rate limit — sugestao: 10 tentativas/minuto por IP

**A2 — Paginacao nos endpoints de listagem**
- `GET /transactions`, `GET /assets` e similares sem `limit/offset` — queries sem LIMIT podem sobrecarregar banco
- Correcao: adicionar parametros `page` e `page_size` (default 50) em todos os endpoints de listagem

**A3 — Routers stub ativos sem implementacao**
- `analysis.py`, `fixed_income.py`, `goals.py`, `quotes.py` estao registrados com apenas 77–78 bytes
- Correcao: ou implementar o minimo (retornar `501 Not Implemented` com mensagem clara) ou remover o registro do `main.py` ate a sprint correspondente

**A4 — Consolidar `quote_service.py` e `quotes_service.py`**
- Dois servicos de cotacao com responsabilidades sobrepostas (3,2 KB vs 13,6 KB)
- Correcao: unificar em `quotes_service.py` e remover `quote_service.py`, ajustando todos os imports

### Itens de MEDIA PRIORIDADE

**M1 — Health check real**
- `GET /health` retorna `{"status": "ok"}` hardcoded sem verificar banco ou Redis
- Correcao: testar `SELECT 1` no banco e ping no Redis; retornar `503` se algum falhar

**M2 — Scheduler com isolamento de falha por job**
- Uma excecao nao tratada em um job pode silenciar os demais
- Correcao: envolver cada job em `try/except` com log estruturado; usar `misfire_grace_time`

**M3 — Cache no `performance_service.py`**
- Recalcula rentabilidade a cada requisicao sem cache
- Correcao: adicionar TTL de 5 minutos no Redis usando o padrao ja existente em `cache.py`

**M4 — Timeout no `logo_service.py`**
- Requisicoes HTTP externas sem timeout configurado
- Correcao: adicionar `timeout=httpx.Timeout(5.0)` nas chamadas do `httpx.AsyncClient`

**Criterios de aceite:**
- C1: erro 500 retorna mensagem generica; traceback aparece apenas em logs do servidor
- C2: toda chamada ao debug router gera log com IP, timestamp e endpoint acessado
- C3: token revogado apos logout retorna 401 em qualquer endpoint protegido
- A1: mais de 10 tentativas de login do mesmo IP em 1 minuto retornam 429
- A2: todos os endpoints de listagem aceitam e respeitam `page`/`page_size`
- A3: endpoints stub retornam `501` ou sao removidos do router
- M1: `/health` retorna `503` se banco ou Redis estiverem inaccessiveis

**Prioridade:** alta — executar antes da Sprint 8.

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

## Sprint 11 - Metas e Alocacao (Distribuicao da Carteira em Configuracoes)

**Objetivo:** permitir que o usuario defina metas percentuais por classe de ativo diretamente em Configuracoes, com visualizacao em grafico de rosca e validacao de total = 100%.

> **Situacao atual (22 Jun 2026):**
> - **Backend 100% pronto:** `routers/class_targets.py` + `services/class_target_service.py` com GET/PUT/DELETE funcionais
> - **Frontend ausente:** `Configuracoes.tsx` nao possui a aba "Distribuicao da Carteira" nem qualquer integracao com os endpoints de class-targets

### Referencia visual
O layout alvo e o seguinte (conforme print de 21 Jun 2026):
- Sidebar de Configuracoes com as abas: Ajustes Gerais, Compartilhar carteira, **Distribuicao da carteira**, Integracao B3
- Painel direito com grafico de rosca (donut chart) refletindo os percentuais em tempo real
- Lista de classes com cor identificadora, campo de percentual com botoes +/- e botao de remover
- Botao "+ Adicionar tipo de ativo" para inserir novas classes
- Rodape com total acumulado (deve atingir exatamente 100%) e botao "Salvar alteracoes"

### Escopo do frontend (a implementar)

**Novos arquivos:**
- `frontend/src/services/classTargetsService.ts` — chamadas a `GET/PUT/DELETE /api/v1/portfolios/{id}/class-targets`
- `frontend/src/hooks/useClassTargets.ts` — hooks React Query: `useClassTargets`, `useUpsertTarget`, `useDeleteTarget`
- `frontend/src/components/configuracoes/DistribuicaoCarteira.tsx` — componente principal do painel

**Alteracoes em arquivos existentes:**
- `frontend/src/pages/Configuracoes.tsx` — adicionar aba "Distribuicao da carteira" e renderizar `<DistribuicaoCarteira />`

### Comportamento esperado
- Ao entrar na aba, carrega as metas salvas via `GET /class-targets`
- Alteracoes no campo de percentual atualizam o grafico de rosca em tempo real (estado local)
- Botao `+` e `-` incrementam/decrementam em 1%; campo editavel diretamente
- Botao de remover chama `DELETE /class-targets/{type}` imediatamente (sem aguardar salvar)
- Total e calculado localmente; se diferente de 100%, o botao "Salvar" fica desabilitado com aviso
- "Salvar alteracoes" dispara um `PUT` para cada classe modificada em paralelo
- Classes disponiveis para adicionar: ACAO, FII, ETF, TESOURO_DIRETO, RENDA_FIXA, CRIPTO, OUTROS
- Cores das fatias do grafico consistentes com as cores de classe ja usadas no sistema

### Criterios de aceite
- Aba "Distribuicao da carteira" aparece em Configuracoes e carrega dados do backend
- Grafico de rosca reflete os percentuais em tempo real ao editar
- Nao e possivel salvar com total diferente de 100%
- Adicionar, editar e remover classes funciona de ponta a ponta
- Comportamento correto quando carteira nao tem nenhuma meta salva (estado vazio com CTA)
- Frontend compila sem erros TypeScript

**Prioridade:** media-alta — backend ja pronto, custo de implementacao baixo.

---

## Sprint 12 - IRPF ⚠️ BACKEND + FRONTEND BASICO JA IMPLEMENTADOS

**Objetivo:** revisar, testar e completar o modulo de IRPF ja existente.

> **Situacao atual (22 Jun 2026 — auditoria):**
> - `irpf_service.py` (24 KB) — implementado
> - `routers/irpf.py` (5.6 KB) — implementado
> - `IRPFPage.tsx` (23.6 KB) — implementado
> - Status documentado anteriormente como Sprint futura (⏳) estava incorreto

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
| Sprint 7 — Rentabilidade | 🔄 Em andamento — 22 Jun 2026 |
| Sprint 7.5 — Hardening Seguranca e Qualidade | 🔜 Apos Sprint 7 |
| Sprint 8 — Historico Patrimonial (frontend) | ⏳ |
| Sprint 9 — Patrimonio por Classe | ⏳ |
| Sprint 10 — Renda Fixa e Tesouro | ⏳ |
| Sprint 11 — Metas e Alocacao (Distribuicao da Carteira) | ⏳ |
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
