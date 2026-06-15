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
- Sem duas fontes de verdade para usuario autenticado

---

## Sprint 2 - Modelo de Transacoes e Servicos Legados ✅ CONCLUIDA

**Objetivo:** alinhar todos os servicos com o modelo atual de transacoes.

**Criterios de aceite atendidos:**
- Testes de transacoes passam com o modelo atual
- Nenhum servico ativo importa `TransactionType` inexistente
- Criacao e exclusao de transacoes atualizam o resumo
- Validacao de venda ativa: impede vender mais do que a posicao atual
- Commits: `c1434e56`, `18fbf392`, `4a4908e7`

---

## Sprint 3 - Padronizacao Async no Backend ✅ CONCLUIDA

**Objetivo:** evitar erros de runtime causados por mistura de `AsyncSession` e `Session`.

**Criterios de aceite atendidos:**
- Todos routers e services ativos usam `AsyncSession`
- Commits: `297b7e8b`, `07b89607`

---

## Sprint 4 - Carteiras, Posicoes e Patrimonio ✅ CONCLUIDA — 15 Jun 2026

**Objetivo:** consolidar o nucleo patrimonial como fonte confiavel do sistema.

**Escopo executado:**
- PM ponderado correto; fees de venda nao afetam PM
- Posicoes zeradas removidas; tipos normalizados
- Resumo com `Optional[float]` para campos sem cotacao
- 23 cenarios de teste em `test_portfolio_service.py`

**Commits:** `a73d9bd7`, `38bed9b3`, `680b489f`, `cc70de49`

---

## Sprint 5 - Cotacoes e Integracoes de Mercado ✅ CONCLUIDA — 15 Jun 2026

**Objetivo:** tornar cotacoes mais robustas e previsiveis; implementar historico patrimonial real via snapshots diarios.

**Escopo executado:**

### Pipeline de cotacoes — 3 camadas
- `asset_types.py`: fonte unica de verdade para tipos de ativo (`INTL_TYPES`, `BRAPI_TYPES`, `NO_QUOTE_TYPES`).
- `Asset.last_price`: campo adicionado (migration 004) — cache L1 no banco.
- `quotes_service.py`: cache L1 (banco) → L2 (memoria 5min) → L3 (API externa).
- `brapi.py`: refatorado com bulk, single e historical; sem raise em falha parcial.
- `price_history_service.py`: OHLCV diario no banco (INSERT ON CONFLICT DO NOTHING).
- `quote_service.py`: `update_all_quotes()` — atualiza `Asset.last_price` para todos os ativos.

### Snapshots diarios de patrimonio
- `PortfolioSnapshot` model + migration 005.
- `portfolio_snapshot_service.py`: backfill retroativo, refresh diario, get_daily_evolution, get_monthly_evolution.
- `performance_service.py`: historico mensal usa snapshots reais (valor de mercado, nao custo).

### Scheduler e endpoints
- `scheduler.py`: 6 jobs; novo job 19h00 = update_all_quotes + refresh_today_snapshot por carteira.
- `routers/performance.py`: 3 novos endpoints:
  - `GET /{id}/evolution/daily?days=365`
  - `GET /{id}/evolution/monthly?months=24`
  - `POST /{id}/evolution/backfill?days_back=N`

**Criterios de aceite atendidos:**
- ✅ Falha em BRAPI/yfinance nao derruba endpoints de posicoes
- ✅ Cotacoes ausentes retornam `None`, nao valores inventados
- ✅ Nacionais via BRAPI, internacionais via yfinance
- ✅ Historico patrimonial diferencia aporte e valor de mercado
- ✅ Scheduler orquestrado com ordem correta (preco antes do snapshot)

**Checklist de deploy:**
1. `alembic upgrade head` (migrations 004 e 005)
2. `POST /portfolios/{id}/evolution/backfill` para cada carteira existente
3. Scheduler 19h00 mantem snapshots atualizados automaticamente

**Commits:**
- `bb258df8` — feat: asset_types.py
- `14f4b50e` — feat: Asset.last_price + migration 004
- `315325e9` — refactor: brapi.py
- `9ea72604` — feat: price_history_service.py
- `9015538d` — feat: quotes_service.py
- `c335b513` — refactor: quote_service.py
- `b4573326` — feat: PortfolioSnapshot + migration 005
- `4a8fbda6` — feat: portfolio_snapshot_service.py
- `c8a57e83` — refactor: performance_service.py
- `f3a91f74` — feat: scheduler.py
- `239bcd92` — feat: routers/performance.py

---

## Sprint 6 - Proventos

**Objetivo:** entregar proventos confiaveis, com modo automatico e manual.

**Escopo:**
- Corrigir backfill de proventos para funcionar com o modelo atual
- Separar provento global do ativo e provento da carteira
- Calcular quantidade na data-ex
- Tratar JCP com valor liquido
- Implementar lancamento manual de proventos
- Exibir historico mensal, distribuicao por ativo, valores recebidos e a receber
- Garantir idempotencia na sincronizacao

**Criterios de aceite:**
- Sincronizar o mesmo ativo duas vezes nao duplica proventos
- Quantidade considerada usa posicao na data-ex
- Dashboard de proventos mostra totais coerentes
- Usuario consegue cadastrar provento manualmente

**Prioridade:** alta.

---

## Sprint 7 - Rentabilidade

**Objetivo:** calcular rentabilidade de forma util para decisao.

**Criterios de aceite:**
- Rentabilidade por ativo bate com transacoes e cotacoes
- Carteira mostra retorno total com e sem proventos
- Ativos vendidos continuam contribuindo para lucro realizado
- Tela nao quebra quando cotacao esta ausente

**Prioridade:** media-alta.

---

## Sprint 8 - Historico Patrimonial

**Objetivo:** evoluir o grafico de patrimonio de aportes acumulados para valor historico real.

> **Nota:** a infraestrutura de snapshots foi antecipada na Sprint 5 (`portfolio_snapshot_service.py`, migration 005, endpoints de evolucao). Sprint 8 focara na integracao frontend (graficos) e refinamentos.

**Escopo atualizado:**
- Integrar endpoints `GET /evolution/daily` e `GET /evolution/monthly` no frontend
- Grafico de linha (evolucao diaria) e grafico de barras (mensal)
- Seletores de periodo: 6m, 12m, 24m, tudo
- Comparativo: valor investido vs valor de mercado

**Criterios de aceite:**
- Grafico diferencia aporte acumulado e valor de mercado
- Periodos funcionam sem erro

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

## Sprint 11 - Metas e Alocacao

**Objetivo:** ajudar o usuario a planejar e rebalancear a carteira.

**Prioridade:** media.

---

## Sprint 12 - IRPF

**Objetivo:** gerar informacoes uteis para declaracao anual.

**Escopo:**
- Posicao em 31/12 por ativo
- Bens e Direitos
- Rendimentos isentos, JCP e tributaveis
- Lucro/prejuizo realizado por mes
- Exportacao relatorio anual
- **Metodo:** Preco Medio Ponderado

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
| Sprint 6 — Proventos | 🔜 Proxima |
| Sprint 7 — Rentabilidade | ⏳ |
| Sprint 8 — Historico Patrimonial (frontend) | ⏳ |
| Sprint 9 — Patrimonio por Classe | ⏳ |
| Sprint 10 — Renda Fixa e Tesouro | ⏳ |
| Sprint 11 — Metas e Alocacao | ⏳ |
| Sprint 12 — IRPF | ⏳ |
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
