# Changelog - SIG v2

Todas as alteracoes relevantes do projeto sao documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Referencias Tecnicas] - Anotacoes para sprints futuras

### Fonte: https://www.traders.com.br/blog/posts/api-financeira-python-mercado-como-usar

---

#### Sprint 5 (Cotacoes e Integracoes de Mercado) — referencias

**yfinance com sufixo `.SA` para acoes brasileiras**
- Acoes BR: ticker com sufixo `.SA` (ex: `PETR4.SA`). Internacionais sem sufixo.
- **Aplicacao:** `backend/app/services/quotes_service.py`

**Cache local com Parquet para historico de cotacoes**
- Salvar cotacoes em `.parquet` e atualizar apenas incrementalmente.
- **Aplicacao:** Sprint 5 e Sprint 8 (Historico Patrimonial).

---

#### Sprint 10 (Renda Fixa e Tesouro Direto) — referencias

**Tesouro Direto via CSV oficial (B3/Tesouro Nacional)**
- URL: `https://www.tesourodireto.com.br/json/br/com/b3/tesouro/tesouro-direto/1/TesouroDireto_HistoricoTaxaPreco.csv`
- **Aplicacao:** `treasury_service.py`

**Banco Central via `python-bcb` (Selic, IPCA, CDI, cambio, IGPM)**
- Instalacao: `pip install python-bcb`
- **Aplicacao:** Sprint 10 / Sprint 12 (IRPF) / Sprint 5 (cambio PTAX).

---

#### Resumo de dependencias a adicionar nas sprints futuras

| Biblioteca | Sprint | Uso |
|---|---|---|
| `python-bcb` | Sprint 5 / Sprint 10 | Selic, IPCA, CDI, PTAX via Bacen |
| `pyarrow` ou `fastparquet` | Sprint 5 / Sprint 8 | Cache de cotacoes em Parquet |

---

## [Sessao] - 2026-06-23 — Hotfix cambio + cotacoes internacionais

### Contexto

Apos Sprint 7 e Sprint 11, o sistema apresentava dois problemas persistentes nos logs:
- `YFRateLimitError` para ativos internacionais (NVDA, IVV, INTR, TFLO) — yfinance com rate limit atingido
- `FALLBACK_RATE=5.70` sendo aplicado para datas historicas USD/BRL — BRAPI nao tem endpoint de historico de cambio funcional

---

### Fix 1 — Alpha Vantage como fonte primaria para ativos internacionais

#### Problema
O `quotes_service` e `price_history_service` usavam yfinance diretamente para `INTL_TYPES` (STOCK, ETF_INTERNACIONAL). O yfinance aplica rate limit agressivo em producao, retornando `YFRateLimitError` silenciosamente e deixando cotacoes em branco.

#### Solucao
- **Novo arquivo:** `backend/app/integrations/alpha_vantage.py`
  - `fetch_quote_batch(tickers)` — cotacoes atuais via `GLOBAL_QUOTE` (limite: 25 req/min)
  - `fetch_price_history(ticker, date_from, date_to)` — historico diario via `TIME_SERIES_DAILY_ADJUSTED`
  - Rate limiter dedicado (`alpha_vantage_limiter`) em `core/rate_limiter.py` — 20 req/min com semaforo asyncio
- **`core/config.py`:** adicionada variavel `ALPHA_VANTAGE_API_KEY`
- **`services/quotes_service.py`:** Alpha Vantage como L2 para `INTL_TYPES`; yfinance rebaixado para L3
- **`services/price_history_service.py`:** Alpha Vantage como L2.5 para historico INTL; yfinance como L3
- **`.env.example`:** documentada a nova variavel com instrucoes de obtencao da chave gratuita

#### Cadeia de cotacoes INTL apos o fix
```
L1 → DB cache (asset.last_price)
L2 → Alpha Vantage (primario)
L3 → yfinance (fallback)
```

**Commits:** `alpha_vantage.py` + atualizacoes em `quotes_service`, `price_history_service`, `config`, `rate_limiter`, `.env.example`

---

### Fix 2 — BCB PTAX como fonte primaria de historico USD/BRL

#### Problema
O `fx_service` chamava `brapi.fetch_currency_history` (`/api/v2/currency/historical`) que retornava `[]` silenciosamente. Investigacao revelou que:
1. A BRAPI nao documenta esse endpoint nas paginas de Moedas — ele nao e suportado de forma confivel.
2. O `fx_service` solicitava ranges que incluiam datas futuras (datas de snapshot de projecao do grafico patrimonial), causando `FALLBACK_RATE=5.70` para todo o periodo.

#### Solucao
- **Novo arquivo:** `backend/app/integrations/bcb.py`
  - `fetch_usd_brl_period(start_date, end_date)` — historico diario PTAX via `CotacaoDolarPeriodo` (OData BCB)
  - `fetch_usd_brl_day(date_str)` — PTAX de um dia especifico via `CotacaoDolarDia`
  - Conversao automatica de `YYYY-MM-DD` para `MM-DD-YYYY` (formato exigido pela API do BCB)
  - Usa `cotacaoVenda` (PTAX venda) como referencia
  - API publica, sem token, historico desde 1994
- **`services/fx_service.py`:** reescrito
  - BCB PTAX como L2 primario (historico e dia atual)
  - AwesomeAPI como fallback
  - **Guard de datas futuras:** qualquer `date_str >= hoje` e redirecionado para `get_usd_brl_today` — elimina chamadas BCB com datas de projecao
  - `get_usd_brl_batch` otimizado: uma unica chamada BCB para todo o range + fallback ao dia util anterior mais proximo (feriados/fins de semana)
  - BRAPI e yfinance removidos do fluxo de cambio

#### Cadeia de cambio apos o fix
```
L2 memoria → L1 banco (fx_rates) → BCB PTAX → AwesomeAPI → FALLBACK_RATE
```

#### Resultado nos logs
Antes:
```
[brapi] fetch_currency_history: sem dados para USD-BRL (2025-06-09 a 2025-08-06)
[fx_service] sem cotacao para 2025-06-09 — usando FALLBACK_RATE=5.70
```
Depois:
```
[bcb] CotacaoDolarPeriodo 2025-06-02 a 2025-06-09: 6 registros
```

**Commits:** `0fa81a4` (bcb.py) · `13fdc49` (fx_service.py)

---

### Arquivos modificados nesta sessao

| Arquivo | Tipo | Descricao |
|---|---|---|
| `backend/app/integrations/alpha_vantage.py` | Novo | Cotacoes e historico de ativos INTL via Alpha Vantage |
| `backend/app/integrations/bcb.py` | Novo | PTAX USD/BRL via API oficial do Banco Central |
| `backend/app/core/config.py` | Alterado | `ALPHA_VANTAGE_API_KEY` adicionado |
| `backend/app/core/rate_limiter.py` | Alterado | `alpha_vantage_limiter` (20 req/min) adicionado |
| `backend/app/services/quotes_service.py` | Alterado | AV como L2 para INTL_TYPES |
| `backend/app/services/price_history_service.py` | Alterado | AV como L2.5 para historico INTL |
| `backend/app/services/fx_service.py` | Reescrito | BCB PTAX primario; guard datas futuras; sem BRAPI/yfinance |
| `.env.example` | Alterado | `ALPHA_VANTAGE_API_KEY` documentado |

---

## [Sessao] - 2026-06-22 (cont.) — Sprint 7.5 parcial + Bugfixes

### Sprint 7.5 — Hardening de Seguranca (C1–C3 concluidos)

---

#### C1 — Traceback exposto em producao removido

**Arquivo:** `backend/app/main.py`

**Problema:** o `global_exception_handler` retornava o stack trace completo na resposta JSON em qualquer ambiente, expondo detalhes internos do servidor para o cliente.

**Correcao:** handler reescrito para logar o traceback internamente via `logging.error` e retornar apenas mensagem generica ao cliente. Em ambiente `DEBUG=true` o detalhe continua visivel.

---

#### C2 — `debug.py` — audit log + rate limiting

**Arquivo:** `backend/app/routers/debug.py`

**Problema:** endpoints de reset de senha e criacao de usuario com qualquer role estavam ativos sem controle, sem log e sem throttling.

**Correcao:**
- `_audit_log()` estruturado adicionado: timestamp, endpoint, IP, user-agent, resultado
- Rate limit de 5 req/min por IP aplicado via `slowapi` em todos os 3 endpoints
- Todos os endpoints recebem `Request` para capturar IP + UA no audit
- Variavel `DEBUG_RATE_LIMIT` no `.env` permite ajustar o limite (default `5/minute`)
- Processo de desativacao documentado no cabecalho do arquivo

**Commit:** `59ba7ff`

---

#### C3 — Refresh token blacklist + endpoints `/refresh` e `/logout`

**Arquivos:**
- `backend/app/core/token_blacklist.py` — novo
- `backend/app/core/security.py` — `jti` adicionado ao payload
- `backend/app/routers/auth.py` — `/refresh` e `/logout` implementados
- `backend/app/schemas/auth.py` — `RefreshRequest` adicionado

**Problema:** logout nao invalidava o refresh token; token permanecia valido ate expirar (7 dias).

**Correcao:**
- `token_blacklist.py`: blacklist em memoria com TTL automatico (expurga tokens vencidos a cada insercao, sem dependencia de Redis); thread-safe via `asyncio.Lock`
- `security.py`: `jti` (UUID) adicionado no payload de refresh tokens
- `POST /auth/refresh`: valida `jti` + blacklist, emite novo par access+refresh
- `POST /auth/logout`: invalida refresh token via `jti` na blacklist
- Fix adicional: `/refresh` corrigido para usar `get_user_by_id` em vez de `get_user_by_email` (commit `c9e5b96`)
- Fix adicional: `MessageResponse` restaurado em `auth.py` apos sobrescrita no C3 (commit `71084de`)

**Commits:** `9ff0e40` + `c9e5b96` + `71084de`

---

### Bugfixes — 22 Jun 2026

---

#### B1 — Modal de lancamento de ativos: abas ocultas em desktop (Renda Fixa, Cripto)

**Arquivo:** `frontend/src/components/modals/TransactionModal.tsx` (ou equivalente com as abas de tipo de ativo)

**Problema:** o container de abas usava `overflow: hidden` + `flexShrink: 0` sem `flexWrap`. Com 8 abas e `maxWidth: 500px`, as ultimas abas (Renda Fixa, Cripto) transbordavam para fora da area visivel no scroll horizontal sem o usuario perceber, tornando impossivel selecionar esses tipos.

**Correcao:** adicionado `flexWrap: 'wrap'` e `rowGap: 4` no container de abas para que elas quebrem em ate 2 linhas em vez de desaparecer.

**Commit:** `ffeb622`

---

#### B2 — PositionTable: Stocks e ETF INT exibiam valores com simbolo R$ sem conversao

**Arquivo:** `frontend/src/components/resume/PositionTable.tsx`

**Problema:** `formatBRL` era chamado diretamente em todos os campos de preco e valor, independente da `currency` do ativo. Stocks e ETF Internacionais (ativos USD) apareciam com `R$` e com o valor bruto em USD sem conversao para BRL.

**Comportamento correto definido:**
- Colunas de preco unitario (P. Medio, P. Atual) e valores individuais: exibir na moeda original do ativo (`USD` → `$`, `BRL` → `R$`)
- Header do grupo (Investido / Atual): exibir em BRL, pois o backend ja converte via `fx_rate` nos campos `total_invested` / `total_value` do `PositionGroup`

**Correcao:**
- `fmtMoney(value, currency)` adicionado em `format.ts`: chama `formatUSD` se `currency === 'USD'`, senao `formatBRL`
- `formatUSD` implementado com `Intl.NumberFormat('en-US', { currency: 'USD' })`
- `PositionTable` e `PositionCard` (mobile) atualizados para usar `fmtMoney(value, position.currency)` nas colunas unitarias
- Totais do grupo (`total_invested`, `total_value`) continuam com `formatBRL`

**Commit:** `2b5542b`

---

#### B3 — Transacoes.tsx: preco e total de ativos USD exibidos com R$

**Arquivo:** `frontend/src/pages/Transacoes.tsx`

**Problema:** `TransactionRow` (desktop) e `TransactionCard` (mobile) chamavam `formatBRL(t.price)` e `formatBRL(total)` sem verificar `t.currency`. Stocks comprados em USD apareciam com `R$`.

**Correcao:** substituido `formatBRL(t.price)` por `fmtMoney(t.price, t.currency)` e `formatBRL(total)` por `fmtMoney(total, t.currency)` em ambos os componentes. Totalizadores do rodape (Compras / Vendas) permanecem em BRL pois sao agregados da pagina atual.

**Commit:** `2b5542b` (mesmo commit do B2)

---

## [Sessao] - 2026-06-22 (Sprint 7 CONCLUIDA + Sprint 11 CONCLUIDA)

### Hotfix — Build Render: MISSING_EXPORT useSetClassTarget

**Arquivo:** `frontend/src/components/resume/PositionTable.tsx`

**Problema:** `PositionTable.tsx` importava `useSetClassTarget` — nome que nunca existiu em `useClassTargets.ts`. O hook correto exportado e `useUpsertClassTarget`. O erro passou pelo `tsc` local (possivel cache) mas foi capturado pelo Rolldown/Vite no build de producao do Render:

```
[MISSING_EXPORT] "useSetClassTarget" is not exported by "src/hooks/useClassTargets.ts"
   src/components/resume/PositionTable.tsx:8:10
```

**Correcao:**
- Linha 8 (import): `useSetClassTarget` → `useUpsertClassTarget`
- Uso no `TargetModal`: `const { mutate, isPending } = useSetClassTarget(portfolioId)` → `useUpsertClassTarget(portfolioId)`

**Commit:** `d66bb70` — deploy realizado com sucesso apos o fix.

---

### Sprint 11 — Metas de Alocacao (Distribuicao da Carteira) — CONCLUIDA

Implementacao completa do frontend para configuracao de metas percentuais por classe de ativo, com migracao da pagina Configuracoes para estrutura de abas.

#### Novos arquivos criados

**`frontend/src/services/classTargetsService.ts`** — commit `ccded3a`
- Servico de chamadas HTTP para os endpoints `GET/PUT/DELETE /portfolios/{id}/class-targets`
- Interface `ClassTarget { asset_type: string; target_pct: number }`
- Tres metodos: `list`, `upsert`, `remove`

**`frontend/src/hooks/useClassTargets.ts`** — commit `ccded3a`
- `useClassTargets(portfolioId)` — query com `enabled: !!portfolioId`
- `useUpsertClassTarget(portfolioId)` — mutation com `invalidateQueries` apos sucesso
- `useDeleteClassTarget(portfolioId)` — mutation com `invalidateQueries` apos sucesso

**`frontend/src/components/configuracoes/DistribuicaoCarteira.tsx`** — commit `ccded3a`
- Lista de metas salvas com edicao inline de percentual
- Botao `Save` aparece somente quando ha draft nao salvo (dirty state por classe)
- Badge `X% alocado` com cor dinamica: verde = 100%, laranja < 100%, vermelho > 100%
- Select de adicionar nova classe filtrado (exclui classes ja configuradas)
- Delete individual por classe (chama `DELETE` imediatamente, sem confirmacao modal)
- Empty state descritivo quando nenhuma meta esta configurada
- Guard: exibe aviso quando `portfolioId` e null (nenhuma carteira selecionada)

#### Arquivo alterado

**`frontend/src/pages/Configuracoes.tsx`** — commit `703d047`

Migracao completa de layout vertical (SectionCards empilhados) para estrutura de 4 abas:

| Aba | Conteudo | Icone |
|---|---|---|
| Conta | ProfileSection + PasswordSection | User |
| Carteiras | CarteirasSection | Wallet |
| Distribuicao | DistribuicaoCarteira (novo) | PieChart |
| Avancado | DangerZone + AdminPanel (superadmin) | Settings2 |

**Commits:**
- `ccded3a` — classTargetsService.ts + useClassTargets.ts + DistribuicaoCarteira.tsx
- `703d047` — Configuracoes.tsx migrado para abas

---

### Sprint 7 — Auditoria, correcao de bugs e rentabilidade

Sessao dedicada a leitura cruzada da documentacao (README, ROADMAP, CHANGELOG) com o codigo real da branch `stable-15jun`, identificacao de divergencias e correcao dos bugs mapeados.

#### Auditoria inicial — divergencias encontradas

| # | Item | Status doc | Status real | Acao |
|---|---|---|---|---|
| 1 | `irpf_service.py` + `IRPFPage.tsx` + `routers/irpf.py` | ROADMAP listava como Sprint 12 (pendente) | Ja implementado (24 KB + 23.6 KB + 5.6 KB) | ROADMAP atualizado |
| 2 | `Proventos.tsx` (69 bytes) | Nao documentado | Arquivo stub/redirect coexistindo com `ProventosPage.tsx` | Identificado como wrapper de roteamento |
| 3 | `analysis.py`, `fixed_income.py`, `goals.py`, `quotes.py` (77-78 bytes) | Item A3 do Sprint 7.5 | Confirmado: stubs ativos sem implementacao | Pendente Sprint 7.5 |
| 4 | L1 (`_db_get_fresh`) nunca populado fora do scheduler | Mapeado no hotfix 18/06 | Confirmado: `_db_set` usava apenas `flush()` sem savepoint | Corrigido nesta sessao |

---

#### Bug 1 — `sum_dividends` ignorava proventos manuais (sem `asset_dividend_id`)

**Arquivo:** `backend/app/services/proventos_service.py`

**Problema:** `INNER JOIN` em `asset_dividends` excluia dividendos manuais (sem `asset_dividend_id`), zerando silenciosamente o `total_12m` quando a carteira tinha so proventos manuais.

**Correcao:** substituido por `OUTERJOIN` com condicao `(ex_date >= cutoff) OR (asset_dividend_id IS NULL)`. Adicionado `g["rentabilidade_pct"] = None` no loop de grupos para contrato completo.

**Commit:** `18ddf58`

---

#### Bug 2 — `rentabilidade_pct` ausente no schema `AssetGroupOut`

**Arquivo:** `backend/app/schemas/portfolio.py`

**Problema:** campo `rentabilidade_pct` nao existia em `AssetGroupOut`; o backend nao serializava o campo para o frontend, gerando erro silencioso na leitura.

**Correcao:** adicionado `rentabilidade_pct: Optional[float] = None` ao schema Pydantic `AssetGroupOut`.

**Commit:** `8e05e0d`

---

#### Bug 3 — dupla formatacao de percentual em `ResumePage.tsx`

**Arquivo:** `frontend/src/pages/ResumePage.tsx`

**Problema:** `KpiCard` ja chama `formatPercent(change)` internamente; passar `formatPercent(variacaoPct)` como `change` resultava em dupla formatacao (`"15.23%"` virava `"1523.00%"`).

**Correcao:** adicionados comentarios inline documentando que `variacaoPct` e `rentabilidade` devem chegar **brutos** (escala `15.23 = 15,23%`) ao `KpiCard`, sem segunda chamada ao `formatPercent`.

**Commit:** `ec36720`

---

#### Bug 4 (raiz) — L1 de cotacoes nunca populado fora do scheduler

**Arquivo:** `backend/app/services/quotes_service.py`

**Problema (raiz):** `_db_set` usava apenas `await db.flush()` — o dado ficava visivel apenas dentro da transacao corrente. Chamadas de `get_portfolio_positions` e `get_portfolio_summary` nao faziam `commit` apos `get_prices`, descartando o `last_price` ao final da request. Na proxima chamada, L1 voltava vazio e o sistema ia para L3 (BRAPI/yfinance) novamente.

**Correcao:**
- `_db_set` reescrito para usar `begin_nested()` (SAVEPOINT SQL). O savepoint commita o `last_price` imediatamente, independente da transacao principal do chamador.
- Se o savepoint falhar (conflito de constraint, etc.), apenas ele faz rollback — a transacao principal nao e afetada. Log de warning emitido.

**Commit:** `f18a0a8`

---

#### A2 — Paginacao server-side no endpoint de transacoes

**Commits:** `a00a1aa` (backend) · `27d0f7b` (frontend)

---

## [Sessao] - 2026-06-18 (fim de dia)

### Hotfix — Tabela de ativos (PositionTable)

**Commits:** `f82c6dc3` (frontend) · `25754acb` (backend)

---

## [Sessao] - 2026-06-15 (fim de dia)

### Manutencao e estabilizacao pos-upgrade

**PRs fechados:** #2, #3 (obsoletos)
**PR mergeado:** #4 — GitHub Actions atualizados
**Correcoes de bugs:** `routers/auth.py`, `routers/portfolios.py`, `frontend/Dockerfile`
**Seguranca:** `reset_pwd.py` removido (commit `febaae6e`)

---

## [Sprint 6] - 2026-06-15

**Commits backend:** `73538f57`, `75790b79`, `ff41314a`, `d2e7b5d5`
**Commits frontend:** `c8ed7f85`, `a6b7ffef`, `670fc7bb`
