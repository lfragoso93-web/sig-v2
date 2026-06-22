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

**Componente `Tabs` criado inline:**
- Estilo pill com fundo `--color-surface-offset` e aba ativa elevada com `--color-surface-2` + shadow
- Aba ativa em `--color-primary`; abas inativas em `--color-text-muted`
- Icone sempre visivel; label visivel a partir de `sm:` (responsive)
- Acessibilidade: `role="tablist"` e `aria-selected` em cada botao
- Sem dependencia externa

**Commits:**
- `ccded3a` — classTargetsService.ts + useClassTargets.ts + DistribuicaoCarteira.tsx
- `703d047` — Configuracoes.tsx migrado para abas

**Criterios de aceite atendidos:**
- ✅ Aba "Distribuicao" aparece em Configuracoes e carrega metas do backend
- ✅ Edicao inline de percentual com salvar individual por classe
- ✅ Badge de total acumulado com feedback visual de cor
- ✅ Adicionar nova classe com select filtrado
- ✅ Remover classe chama DELETE imediatamente
- ✅ Estado vazio com mensagem descritiva
- ✅ Pagina Configuracoes organizada em 4 abas (Conta / Carteiras / Distribuicao / Avancado)
- ✅ Frontend compila sem erros TypeScript

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

**Problema secundario:** a fase de persistencia fazia um segundo `AssetType(raw_type)` que podia lancar `ValueError` silenciosamente, impedindo que `_db_set` fosse chamado para ativos com `asset_type` nao canonico.

**Correcao:**
- `_db_set` reescrito para usar `begin_nested()` (SAVEPOINT SQL). O savepoint commita o `last_price` imediatamente, independente da transacao principal do chamador.
- Se o savepoint falhar (conflito de constraint, etc.), apenas ele faz rollback — a transacao principal nao e afetada. Log de warning emitido.
- `type_map: dict[str, AssetType | None]` adicionado em `get_prices` para reutilizar o `asset_type` ja resolvido na fase de roteamento, eliminando o segundo `try/except ValueError`.
- Ativos com `asset_type` invalido recebem log de warning em vez de falhar silenciosamente.

**Fluxo apos a correcao:**
```
1a requisicao (L1 vazio):
  get_portfolio_positions -> get_prices -> L3 (BRAPI/yfinance)
                                        -> _db_set -> begin_nested() -> COMMIT savepoint
                                        -> L1 populado imediatamente

2a requisicao (ate 15 min depois):
  get_prices -> _db_get_fresh -> L1 hit -> retorna sem chamar L3
```

**Commit:** `f18a0a8`

---

#### A2 — Paginacao server-side no endpoint de transacoes

**Arquivos alterados:**
- `backend/app/schemas/transaction.py` — novo schema `PagedTransactions { items, total, page, page_size, pages }`
- `backend/app/services/transaction_service.py` — novo servico com `COUNT` + `OFFSET/LIMIT`
- `backend/app/routers/transactions.py` — `GET /{portfolio_id}/transactions` aceita `page`, `page_size`, `ticker`, `operation`, `date_from`, `date_to`
- `frontend/src/hooks/useTransactions.ts` — interface `PagedTransactions` + `TransactionFilters`; hook retorna `PagedTransactions` em vez de `Transaction[]`; `placeholderData: prev => prev` para evitar flash ao virar pagina
- `frontend/src/pages/Transacoes.tsx` — filtros server-side via `queryKey`; `totalRecords` vem do servidor; componente `Pagination` com `ChevronLeft/Right`; agrupamento client-side mantido sobre a pagina atual (<=50 itens)

**Breaking change:** endpoint antes retornava `List[TransactionOut]` (array puro), agora retorna `{ items, total, page, page_size, pages }`. Frontend ja adaptado.

**Commits:** `a00a1aa` (backend) · `27d0f7b` (frontend)

---

#### Sprint 7 — logica de rentabilidade (backend)

**Status: IMPLEMENTADA E REVISADA em `portfolio_service.py`**

A revisao do `portfolio_service.py` revelou que toda a logica de rentabilidade ja estava corretamente implementada:

| Campo | Origem | Descricao |
|---|---|---|
| `total_gain` / `variacao_valor` | `current_value - total_invested` | Ganho bruto de capital |
| `total_gain_pct` / `variacao_percentual` | `total_gain / total_invested * 100` | Variacao percentual do capital |
| `lucro_total` | `total_gain + proventos_em_carteira` | Capital + proventos (ativos em carteira) |
| `rentabilidade_total` | `lucro_total / total_invested * 100` | Rentabilidade real ponta a ponta |
| `variation_pct` (grupo) | P4: apenas posicoes cotadas | Variacao do grupo (cotados) |
| `rentabilidade_pct` (grupo) | P3: ganho_cotados + proventos_grupo | Rentabilidade do grupo com proventos |

**Funcoes helper implementadas:**
- `sum_dividends_for_tickers`: proventos apenas dos tickers ainda em carteira (evita superestimativa)
- `sum_dividends_by_ticker`: GROUP BY ticker para calcular rentabilidade por grupo sem N roundtrips
- `normalize_type` / `_TYPE_ALIASES`: eliminam `ValueError` silencioso por alias de `asset_type`

**ResumePage.tsx** consumia todos os campos corretamente com os comentarios anti-dupla-formatacao ja presentes.

**Conclusao Sprint 7:** todos os itens do backlog estao completos. Sprint encerrada.

---

#### Observacao sobre IRPF

Auditoria revelou que `irpf_service.py` (24 KB), `routers/irpf.py` (5.6 KB) e `IRPFPage.tsx` (23.6 KB) ja estavam implementados, contradizendo o ROADMAP que listava IRPF como Sprint 12 (pendente). ROADMAP atualizado para refletir o status real: **backend + frontend basico implementados**, Sprint 12 reservada para revisao e testes.

---

## [Sessao] - 2026-06-18 (fim de dia)

### Hotfix — Tabela de ativos (PositionTable)

Sessao dedicada a correcao de tres bugs visuais e de dados na tabela de ativos do Resumo da carteira.

#### Problemas identificados

| # | Sintoma | Causa raiz |
|---|---|---|
| 1 | Cards grandes + linha de tabela aparecendo juntos | `md:hidden` / `hidden md:block` do Tailwind sem breakpoints configurados — ambos os blocos eram renderizados simultaneamente |
| 2 | Coluna "P. Atual" sempre exibindo `—` | `quotes_service.get_prices` retorna `None` para ativos sem cotacao recente na tabela `assets`; comportamento correto, mas revelou dependencia de L1 (DB cache) vazio |
| 3 | Coluna "Valor Atual" repetindo o "Total Investido" | `enrich_with_prices` fazia fallback `current_value = total_invested` quando `price is None`, mascarando a ausencia de cotacao |

#### Correcoes aplicadas

**Frontend — `frontend/src/components/resume/PositionTable.tsx`**
- Substituido `className="md:hidden"` / `className="hidden md:block"` por hook `useIsDesktop()` com `window.matchMedia('(min-width: 768px)')`
- Renderizacao condicional: `{!isDesktop && <cards>}` e `{isDesktop && <tabela>}` — nunca os dois simultaneamente
- Coluna "Valor Atual" na tabela desktop agora exibe `—` quando `current_price === null`
- Card mobile: "Valor Atual" exibe `—` quando `current_price === null` (nao mais repete investido)
- `hasQuote` corrigido: `current_price !== null && current_price !== undefined` (antes comparava com `average_price`)
- Chave React corrigida: `item.id ?? item.ticker` (antes podia usar `item.id` undefined)
- **Commit:** `f82c6dc3`

**Backend — `backend/app/services/portfolio_service.py`**
- `enrich_with_prices`: quando `price is None`, agora retorna `current_price=None` e `current_value=None` em vez de `current_value=total_invested`
- `get_portfolio_positions`: expoe `current_price=None` / `current_value=None` explicitamente no payload
- Calculo de alocacao e soma de `total_current` usa `current_value or total_invested` (fallback so para alocacao percentual, nao para exibicao)
- Adicionado campo `id` sintetico (`idx + 1`) em cada posicao para uso como chave React
- **Commit:** `25754acb`

**Backend — `backend/app/schemas/position.py`**
- `PositionOut.current_value` alterado de `float` para `Optional[float]` — reflete ausencia de cotacao
- `PositionOut.id` adicionado como `Optional[int]` — id sintetico para chave React
- **Commit:** `25754acb`

#### Comportamento apos os hotfixes

| Campo | Sem cotacao | Com cotacao |
|---|---|---|
| P. Atual | `—` | `R$ XX,XX` |
| Valor Atual | `—` | `R$ XX,XX` |
| Resultado | `—` | `+R$ X,XX (+X,XX%)` |
| Layout | Cards (mobile) | Tabela (desktop) — nunca ambos juntos |

---

## [Sessao] - 2026-06-15 (fim de dia)

### Manutencao e estabilizacao pos-upgrade

Sessao dedicada a limpeza de PRs obsoletos, correcao de bugs criticos de inicializacao do backend e atualizacao da infraestrutura Docker/CI.

#### PRs fechados (obsoletos)
- **PR #2** fechado — pacotes pip (`python-multipart`, `pytest`, `python-jose`) ja estavam atualizados na `main` com versoes mais recentes.
- **PR #3** fechado — Vite 5→8, Tailwind 3→4, TypeScript 5→6 ja aplicados diretamente na `main`.

#### PR mergeado
- **PR #4** mergeado (squash) — GitHub Actions core group: `checkout v6`, `setup-python v6`, `setup-node v6`, `dependency-review v5`. Commit: `450377b9`.

#### Correcoes de bugs — Backend

| Arquivo | Problema | Correcao | Commit |
|---|---|---|---|
| `backend/app/routers/auth.py` | `ImportError`: `get_password_hash` e `create_jwt_token` inexistentes em `security.py` (renomeados na migracao passlib→bcrypt nativo) | `get_password_hash` → `hash_password`; `create_jwt_token({...})` → `create_access_token(subject=str(...))` | `3f98e74f` |
| `backend/app/routers/portfolios.py` | `ModuleNotFoundError: No module named 'app.core.auth'` — modulo renomeado para `deps.py` | `from app.core.auth` → `from app.core.deps` | `d8bc50a5` |

#### Correcoes de infraestrutura

| Arquivo | Problema | Correcao | Commit |
|---|---|---|---|
| `frontend/Dockerfile` | `npm ci` falha sem `package-lock.json` no repositorio | Fallback condicional: `if [ -f package-lock.json ]; then npm ci; else npm install; fi` | `1b4eb493` |
| `frontend/package-lock.json` | Arquivo ausente — impedia builds reproduziveis | Gerado localmente e commitado | `8d7a99a9` |

#### Seguranca
- `reset_pwd.py` removido do repositorio — continha senha `Admin@123` em texto claro. Commit: `febaae6e`.
- Arquivo ainda presente no historico do git (commit `8d7a99a9`). Recomendado usar `git filter-repo` para limpeza completa e trocar a senha nos ambientes.

---

## [Sprint 6] - 2026-06-15

### Objetivo
Entregar proventos confiaveis para a pagina de Proventos: proventos dos ativos da carteira com valor por unidade, valor total pelo usuario, separados em recebidos e futuros. Frontend conectado ao backend com filtros, historico e sincronizacao manual.

---

### Decisoes de modelagem (Sprint 6)

#### Modelo de dois niveis — mantido e consolidado

| Tabela | Papel |
|---|---|
| `asset_dividends` | Provento global do ativo (ex_date, payment_date, value_per_unit, source). Alimentado pelo backfill via BRAPI/yfinance. |
| `dividends` | Provento da carteira especifica. Vincula portfolio + asset_dividend. Armazena quantity (cotas na data-ex), total_value e net_value calculados, status (RECEBIDO/A_RECEBER). |

#### Regras de calculo
- `total_value = quantity * value_per_unit`
- `net_value = total_value * 0.85` para JCP (IR 15%); `= total_value` para os demais
- `status = RECEBIDO` se `payment_date <= hoje`; caso contrario `A_RECEBER`
- `quantity` = posicao liquida (compras - vendas) na data-ex, calculada a partir de `Transaction` por `(portfolio_id, ticker, date <= ex_date)`

#### Tipos sem proventos via API (SKIP_TYPES)
- `CRIPTO`, `TESOURO_DIRETO`, `RENDA_FIXA` — ignorados silenciosamente pelo backfill

---

### Alteracoes — Backend

#### dividend_backfill_service.py — correcoes criticas
- **`_net_qty_on_date`:** corrigido para filtrar por `(portfolio_id, ticker, date)` — `Transaction` nao tem `asset_id`.
- **`_portfolios_with_asset`:** renomeado para `_portfolios_with_ticker`; busca por `ticker` em vez de `asset_id`.
- **`_upsert_portfolio_dividend`:** assinatura atualizada para receber `ticker`.
- **Tipos alinhados com `asset_types.py`:** `YF_TYPES = INTL_TYPES` (importado); `SKIP_TYPES` consolidado.
- **`OperationType.buy`:** comparacao via enum em vez de string livre.
- **Commit:** `73538f57`

#### proventos_service.py — reescrita completa
- Migrado de `Session` sincrona + `db.query()` para `AsyncSession` + `select()`.
- Removidos imports de schemas inexistentes (`app.schemas.dividend`).
- Retorna dicts puros — o router serializa.
- **Funcoes disponiveis:**
  - `get_summary(db, portfolio_id)` — total_recebido, total_a_receber, total_12m, media_mensal_12m
  - `list_items(db, portfolio_id, status, year, asset_type, page, page_size)` — listagem paginada com todos os campos
  - `get_monthly_history(db, portfolio_id, status, asset_type)` — historico por ano/mes
  - `get_distribution(db, portfolio_id, months)` — distribuicao percentual por ativo
- **Commit:** `75790b79`

#### routers/proventos.py — reescrita completa
- Migrado de sincrono para `async def` + `AsyncSession`.
- Removido prefixo `/api/v1` hardcoded (gerenciado pelo `main.py`).
- Removidos schemas inexistentes; resposta e o dict puro do service.
- Validacao de `status` via `DividendStatus` enum — retorna 422 com mensagem clara.
- **Endpoints disponibilizados:**
  - `GET /portfolios/{id}/proventos/summary`
  - `GET /portfolios/{id}/proventos` (filtros: status, year, asset_type, page)
  - `GET /portfolios/{id}/proventos/historico-mensal`
  - `GET /portfolios/{id}/proventos/distribuicao`
- **Commit:** `ff41314a`

#### routers/dividends.py — novo endpoint de sync manual
- **`POST /portfolios/{id}/dividends/sync`:** busca todos os tickers distintos da carteira via `Transaction` e dispara um `BackgroundTask` por ticker chamando `_run_backfill`. Retorna 202 Accepted com lista de tickers enfileirados.
- Reutiliza `_run_backfill` (sessao independente, mesmo padrao de `transactions.py`).
- **Commit:** `d2e7b5d5`

---

### Alteracoes — Frontend

#### frontend/src/services/proventosService.ts
- `ProventosSummary` alinhada com backend: `total_recebido`, `total_a_receber`, `total_12m`, `media_mensal_12m`
- `getDistribution` → `getDistribuicao`; URL corrigida para `/proventos/distribuicao`
- `getEvolucao` removido (endpoint nao existe no backend)
- `getList` agora aponta para `/portfolios/{id}/proventos`; retorna `ProventosListResponse` paginado
- Adicionado `sync()` → `POST /portfolios/{id}/dividends/sync`
- **Commit:** `c8ed7f85`

#### frontend/src/hooks/useProventos.ts
- `useProventosDistribution` renomeado para `useProventosDistribuicao`
- `useProventosEvolucao` removido
- `useSyncProventos` adicionado
- **Commit:** `a6b7ffef`

#### frontend/src/pages/ProventosPage.tsx
- KPIs alinhados com backend: total_recebido, total_a_receber, total_12m, media_mensal_12m
- Botao de sync disparando `useSyncProventos`
- Lista paginada com todos os campos
- **Commit:** `670fc7bb`
