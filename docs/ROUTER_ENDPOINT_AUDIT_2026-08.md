# Auditoria de routers e endpoints — 07/08/2026

Issue executora: #247

## Objetivo

Inventariar as superfícies HTTP registradas no `app.main`, classificando cada router por papel arquitetural antes de qualquer remoção ou refatoração. Este documento não autoriza mudança funcional por si só; ele registra a fronteira atual e os candidatos a investigação.

## Classificação

- **CANÔNICO** — contrato ativo e alinhado à arquitetura atual.
- **COMPATIBILIDADE** — superfície antiga preservada temporariamente; requer consumidor comprovado ou plano de remoção.
- **PLACEHOLDER** — endpoint deliberadamente não implementado; não deve ser apresentado como módulo funcional pronto.
- **OPERACIONAL** — endpoint que dispara mutação/backfill/rebuild e exige revisão específica sob o gate #227.
- **CONDICIONAL/ADMIN** — superfície restrita por debug/admin/configuração.
- **DESCOBERTA/PROVIDER** — endpoint interativo que pode consultar provider, mas não participa de cálculo financeiro canônico.
- **EM AUDITORIA** — não classificado definitivamente até revisão de consumidores e contratos.

## Achados comprovados

### Análise de Carteira — PLACEHOLDER

- Router: `backend/app/routers/analysis.py`.
- Prefixo registrado: `/api/v1/analysis`.
- Comportamento atual: `501 Not Implemented`.
- Metadata antiga de sprint removida.
- A Issue #57 está bloqueada e será redesenhada junto com Metas (#246).
- Não criar novos endpoints ou persistência antes do macroprojeto #246 + #57.

### Renda Fixa — PLACEHOLDER DE API

- Router: `backend/app/routers/fixed_income.py`.
- Prefixo registrado: `/api/v1/fixed-income`.
- Comportamento atual: `501 Not Implemented`.
- Metadata antiga de sprint removida.
- O domínio financeiro de Renda Fixa já possui valuation, contratos e serviços canônicos em outras superfícies; portanto esse placeholder não deve ser interpretado como ausência do domínio.
- Antes de remover ou substituir o router, confirmar se existe consumidor externo documentado.

### Proventos — CANÔNICO

- Router: `backend/app/routers/proventos.py`.
- Prefixo efetivo: `/api/v1/portfolios/{portfolio_id}/proventos`.
- Frontend usa `frontend/src/services/proventosService.ts` nessa superfície.
- Contrato deriva direitos sob demanda de `asset_dividends` e posição histórica.

### Dividends — COMPATIBILIDADE LEGADA EM AUDITORIA

- Router: `backend/app/routers/dividends.py`.
- Endpoint: `GET /api/v1/portfolios/{portfolio_id}/dividends`.
- Service: `backend/app/services/dividend_service.py`.
- Schema: `backend/app/schemas/dividend.py`, onde `DividendResponse` é alias de compatibilidade de `DividendRead`.
- Frontend canônico usa `/proventos`.
- O endpoint é read-only e projeta direitos sob demanda, portanto não viola a arquitetura atual de persistência.
- Não remover apenas por ausência no frontend: confirmar testes, documentação e possíveis consumidores externos.

### Histórico de preços — CANÔNICO DB-FIRST

- Router: `backend/app/routers/prices.py`.
- Endpoint: `GET /api/v1/prices/{ticker}/history`.
- Leitor: `price_history_service.get_price_history`.
- O request é somente leitura do banco e não consulta provider nem dispara backfill.
- A docstring antiga que dizia buscar automaticamente dados desatualizados foi corrigida.
- Gate estrutural em `test_price_history_router_db_first.py` impede imports de integrações/backfills no router.

### Performance backfill — OPERACIONAL EM AUDITORIA

- Router: `backend/app/routers/performance.py`.
- Endpoint mutável: `POST /api/v1/performance/{portfolio_id}/evolution/backfill`.
- Reconstrói snapshots consolidados e por classe.
- Exige autenticação e ownership, mas é uma operação de reconstrução exposta na API comum.
- Busca indexada não encontrou consumidor explícito pelo endpoint/funções; isso não é evidência suficiente para remoção.
- Requer decisão específica sob #227: manter, restringir, mover para superfície operacional/admin ou remover após caracterização.

### Transactions — ALTA PRIORIDADE DE AUDITORIA

- Router: `backend/app/routers/transactions.py`.
- CRUD de transações é funcional e esperado.
- Após `POST`/`PATCH`, o router agenda `run_onboarding` e `_run_backfill` como `BackgroundTasks`.
- `run_onboarding` chama `sync_asset_market_data(full=True, sync_prices=True, sync_logo=True, sync_events=True, commit=True)`.
- O pipeline consulta providers externos e persiste preços/eventos.
- `_run_backfill` chama `backfill_dividends`, que também consulta fontes externas.
- Portanto uma mutação normal de transação pode iniciar sincronização externa automaticamente.
- Isso entra em tensão com o gate #227, que exige seeds/syncs/rebuilds externos explícitos e opt-in.
- Não alterar ainda: caracterizar testes, efeitos esperados e separar atualização derivada local (snapshots/cache) de ingestão externa antes da correção.

### Assets — FRONTEIRA MISTA

`backend/app/routers/assets.py` contém duas famílias distintas:

**Leitura/persistência local:**
- `GET /api/v1/assets/`;
- `GET /api/v1/assets/{ticker}/detail` (histórico persistido; cotação atual ainda usa fachada de quotes);
- `GET /api/v1/assets/search`;
- `POST /api/v1/assets/`.

**Descoberta/provider interativa:**
- `GET /api/v1/assets/suggest`;
- `GET /api/v1/assets/tesouro/search`;
- `GET /api/v1/assets/tesouro/price`;
- `GET /api/v1/assets/quote/{ticker}`.

Essas superfícies de descoberta podem consultar BRAPI/Yahoo e não devem ser confundidas com contratos financeiros DB-first. A auditoria deve manter essa fronteira explícita e impedir que esses endpoints sejam reutilizados dentro de cálculo financeiro canônico.

### Debug — CONDICIONAL/ADMIN SENSÍVEL

- Router: `backend/app/routers/debug.py`.
- Permite listar usuários, redefinir senha e criar usuário/role.
- É condicionado por `APP_DEBUG` ou `ADMIN_SECRET` no `app.main` e exige `X-Admin-Secret`.
- Possui rate limiting e logs estruturados.
- Não classificado como legado neste momento; permanece superfície operacional sensível que deve ser desabilitada em produção quando não necessária.

## Fronteiras já confirmadas no frontend

- `/carteira/proventos` usa `proventosService.ts` e a API `/portfolios/{id}/proventos`.
- `/carteira/metas` existe, mas `goals` permanece fora do escopo funcional até #246/#57.
- `/metas` e `/irpf` são redirects de compatibilidade explícitos.
- Não há rota de Análise atualmente registrada no frontend protegido.

## Prioridades da próxima rodada

1. **P0/P1:** caracterizar e desacoplar ingestão externa automática do CRUD de `transactions`, preservando apenas recomputações locais necessárias.
2. **P1:** decidir destino do POST de backfill de `performance` após comprovar consumidores/testes.
3. **P1:** revisar `assets.detail`/fachada de preços para separar claramente cotação live de leitura persistida.
4. **P2:** continuar inventário de `admin`, `portfolios`, `positions`, `quotes`, `rentabilidade`, `irpf` e `class_targets`.
5. **P2:** decidir remoção de placeholders/compatibilidades somente após prova de ausência de consumidores.

## Regra de remoção

Nenhum endpoint de compatibilidade será removido somente por não aparecer no frontend. Para remoção segura, exigir ao menos:

- busca de consumidores no repositório;
- revisão de testes e documentação;
- classificação na #247;
- decisão explícita de compatibilidade;
- teste de regressão que impeça reintrodução quando aplicável.
