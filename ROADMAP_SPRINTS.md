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
- Commits: `c1434e56` (transaction_service), `18fbf392` (testes), `4a4908e7` (validacao venda)

---

## Sprint 3 - Padronizacao Async no Backend ✅ CONCLUIDA

**Objetivo:** evitar erros de runtime causados por mistura de `AsyncSession` e `Session`.

**Criterios de aceite atendidos:**
- Todos routers e services ativos usam `AsyncSession`
- Nenhum endpoint ativo chama `db.query(...)` sobre `AsyncSession`
- `performance_service.py` e `routers/performance.py` migrados
- Commits: `297b7e8b` (performance_service), `07b89607` (router performance)

---

## Sprint 4 - Carteiras, Posicoes e Patrimonio ✅ CONCLUIDA — 15 Jun 2026

**Objetivo:** consolidar o nucleo patrimonial como fonte confiavel do sistema.

**Escopo executado:**
- Revisao e correcao do calculo de Preco Medio Ponderado
- Vendas reduzem custo proporcional sem alterar PM
- Fees de venda nao entram no PM
- Posicoes zeradas removidas (renda variavel e Tesouro Direto)
- Tipos de ativo normalizados via `normalize_type()`
- Resumo: `total_current`, `result_abs`, `result_pct` retornam `None` quando sem cotacao
- Resumo calculado apenas sobre ativos com cotacao disponivel
- Contrato da API: `PositionItem` e `SummaryResponse` com `Optional[float]` para campos dependentes de cotacao
- Testes reescritos cobrindo todos os criterios de aceite (23 cenarios em `test_portfolio_service.py`)

**Criterios de aceite atendidos:**
- ✅ Calculos de posicao possuem testes
- ✅ Ativos sem cotacao: `current_price = null`, sem usar PM como cotacao
- ✅ `current_value`, `result_abs`, `result_pct` tambem `null` sem cotacao
- ✅ Resumo bate com as posicoes (calcula sobre ativos com cotacao)
- ✅ Carteiras de usuarios diferentes ficam isoladas
- ✅ Tesouro Direto controlado por cotas (mesmo comportamento que renda variavel)
- ✅ fees de venda nao alteram PM nem custo da posicao restante

**Commits:**
- `a73d9bd7` — refactor(sprint4): corrigir enrich_with_prices, recalc_positions e remover import Session morto
- `38bed9b3` — refactor(sprint4): ajustar PositionItem e SummaryResponse para campos nullable
- `680b489f` — test(sprint4): reescrever testes de portfolio_service cobrindo todos os criterios de aceite
- `cc70de49` — docs(sprint4): registrar Sprint 4 no CHANGELOG

---

## Sprint 5 - Cotacoes e Integracoes de Mercado

**Objetivo:** tornar cotacoes mais robustas e previsiveis.

**Escopo:**
- Revisar integracao BRAPI para acoes, FIIs, ETFs nacionais, cripto e Tesouro
- Revisar yfinance para stocks e ETFs internacionais
- Criar tratamento claro para falha externa
- Padronizar cache em memoria ou Redis
- Criar endpoint de cotacao por ticker, se necessario
- Registrar logs suficientes para diagnosticar falhas de API externa
- Revisar variaveis de ambiente usadas por integracoes

**Criterios de aceite:**
- Falha em BRAPI/yfinance nao derruba endpoint de posicoes
- Cotacoes ausentes retornam ausentes, nao valores inventados
- Tickers internacionais e nacionais usam provedores corretos
- Configuracoes ausentes sao tratadas com fallback claro

**Prioridade:** alta.

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

**Escopo:**
- Snapshots diarios ou mensais da carteira
- Valor investido e valor de mercado por data
- Historico de precos quando disponivel
- Periodos: 6m, 12m, 24m e tudo

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
- **Metodo:** Preco Medio Ponderado (mesmo que `portfolio_service.py`)

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
| Sprint 5 — Cotacoes e Integracoes | 🔜 Proxima |
| Sprint 6 — Proventos | ⏳ |
| Sprint 7 — Rentabilidade | ⏳ |
| Sprint 8 — Historico Patrimonial | ⏳ |
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
