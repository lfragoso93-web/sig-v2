# Auditoria de routers e endpoints — 07/08/2026

Issue executora: #247

## Objetivo

Inventariar as superfícies HTTP registradas no `app.main`, classificando cada router por papel arquitetural antes de qualquer remoção ou refatoração. Este documento registra a fronteira atual, os achados corrigidos e os candidatos ainda em investigação.

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
- O domínio financeiro de Renda Fixa já possui valuation, contratos e serviços canônicos em outras superfícies.
- Antes de remover o router, confirmar ausência de consumidor externo documentado.

### Quotes — PLACEHOLDER REDUNDANTE EM AUDITORIA

- Router: `backend/app/routers/quotes.py`.
- Prefixo registrado: `/api/v1/quotes`.
- Retorna `501` e declara que a funcionalidade é coberta por `/api/v1/prices`.
- Busca indexada não encontrou consumidor da rota.
- Candidato à remoção física após fechar a prova de consumidores/imports, sem confundir o router placeholder com `quotes_service`, que continua sendo infraestrutura interna de cotações.

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

### Performance — READ-ONLY APÓS CORREÇÃO

- Router: `backend/app/routers/performance.py`.
- O antigo `POST /api/v1/performance/{portfolio_id}/evolution/backfill` permitia reconstrução de snapshots pela API comum de usuário.
- Nenhum consumidor frontend/repositório foi encontrado para a porta HTTP.
- A porta HTTP pública foi removida; os serviços internos de backfill/rebuild permanecem disponíveis para fluxos operacionais explícitos.
- O router agora contém somente GETs de leitura/reconciliação.
- Gate `test_performance_router_read_only.py` impede reintrodução de `@router.post`, da rota de backfill e de imports dos rebuilders.

### Transactions — CRUD CANÔNICO, SYNC EXTERNO DESACOPLADO

- Router: `backend/app/routers/transactions.py`.
- CRUD de transações permanece funcional.
- O comportamento anterior agendava `run_onboarding` e backfill de Proventos após `POST`/`PATCH`, iniciando providers externos automaticamente.
- Essa ingestão externa foi removida do CRUD.
- Permanecem efeitos locais necessários: cadastro básico do ativo, atualização derivada de Renda Fixa/Tesouro quando aplicável, snapshots e invalidação de cache.
- Gate `test_transactions_no_automatic_market_sync.py` impede reintrodução de onboarding/pipeline/backfill de mercado no router.

### Positions — CANÔNICO DB-FIRST APÓS CORREÇÃO

- Router: `backend/app/routers/positions.py`.
- Os GETs de posições e resumo aceitavam `refresh=true`, que chamava `update_quotes_for_portfolio` durante o request financeiro.
- Busca indexada não encontrou consumidor do contrato `refresh`.
- O parâmetro e a chamada de atualização foram removidos.
- As superfícies agora leem exclusivamente dados persistidos e delegam cálculo ao `portfolio_service`.
- Gate `test_positions_router_db_first.py` impede reintrodução do refresh ou de `quotes_service` no router.

### Rentabilidade — CANÔNICO DB-FIRST

- Router: `backend/app/routers/rentabilidade.py`.
- Expõe somente GETs de KPIs, resultados por ativo/classe, benchmarks persistidos e reconciliação.
- Benchmarks são lidos exclusivamente do banco.
- Nenhum endpoint mutável/rebuild foi identificado nesta superfície.

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

Essas superfícies de descoberta podem consultar provider e não devem ser confundidas com contratos financeiros DB-first. A auditoria deve manter essa fronteira explícita e impedir que sejam reutilizadas dentro de cálculo financeiro canônico.

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
- `performanceService.ts` não expõe backfill; a busca indexada também não encontrou consumidor da rota removida.

## Prioridades da próxima rodada

1. **P1:** revisar `assets.detail`/fachada de preços e separar cotação live de leitura persistida quando a página for financeira.
2. **P1:** fechar prova de consumidores do router placeholder `quotes` e, se confirmada, removê-lo sem tocar em `quotes_service`.
3. **P1/P2:** revisar `portfolios`, `admin`, `irpf` e `class_targets` por mutações/aliases redundantes.
4. **P2:** decidir destino de `dividends` após prova de consumidores externos.
5. **P2:** revisar `performanceService.ts`, cuja rota histórica precisa ser comparada com a superfície backend atual antes de decidir remoção do client órfão.

## Regra de remoção

Nenhum endpoint de compatibilidade será removido somente por não aparecer no frontend. Para remoção segura, exigir ao menos:

- busca de consumidores no repositório;
- revisão de testes e documentação;
- classificação na #247;
- decisão explícita de compatibilidade;
- teste de regressão que impeça reintrodução quando aplicável.
