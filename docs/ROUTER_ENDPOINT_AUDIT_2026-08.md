# Auditoria de routers e endpoints — 07/08/2026

Issue executora: #247

## Objetivo

Inventariar as superfícies HTTP registradas no `app.main`, classificando cada router por papel arquitetural antes de qualquer remoção ou refatoração. Este documento registra a fronteira atual, os achados corrigidos e os candidatos ainda em investigação.

## Regra canônica de providers

A partir deste checkpoint, a auditoria usa a seguinte regra como critério obrigatório:

- antes de carteiras reais, o ambiente executa bootstrap completo e persistente;
- após o bootstrap, requests funcionais são DB-first;
- providers externos em runtime só podem ser consultados para **preço intraday** e **preço de fechamento diário**;
- qualquer outro endpoint que consulte provider diretamente é desvio arquitetural até que seja migrado para leitura persistida ou para o bootstrap operacional.

## Classificação

- **CANÔNICO** — contrato ativo e alinhado à arquitetura atual.
- **COMPATIBILIDADE** — superfície antiga preservada temporariamente; requer consumidor comprovado ou plano de remoção.
- **PLACEHOLDER** — endpoint deliberadamente não implementado; não deve ser apresentado como módulo funcional pronto.
- **OPERACIONAL** — operação explícita de bootstrap/rebuild/manutenção, fora de requests funcionais comuns.
- **CONDICIONAL/ADMIN** — superfície restrita por debug/admin/configuração.
- **PREÇO LIVE** — consulta externa permitida apenas para intraday/fechamento, com persistência antes do uso financeiro.
- **DESVIO PROVIDER** — request funcional que consulta provider fora da exceção de preço; requer correção.
- **EM AUDITORIA** — não classificado definitivamente até revisão de consumidores e contratos.

## Achados comprovados

### Análise de Carteira — PLACEHOLDER

- Router: `backend/app/routers/analysis.py`.
- Prefixo registrado: `/api/v1/analysis`.
- Comportamento atual: `501 Not Implemented`.
- Metadata antiga de sprint removida.
- A Issue #57 está bloqueada e será redesenhada junto com Metas (#246).

### Renda Fixa — PLACEHOLDER DE API

- Router: `backend/app/routers/fixed_income.py`.
- Prefixo registrado: `/api/v1/fixed-income`.
- Comportamento atual: `501 Not Implemented`.
- Metadata antiga de sprint removida.
- O domínio financeiro já existe em outras superfícies; o placeholder não representa ausência do domínio.

### Quotes — PLACEHOLDER REDUNDANTE EM AUDITORIA

- Router: `backend/app/routers/quotes.py`.
- Prefixo registrado: `/api/v1/quotes`.
- Retorna `501` e declara que a funcionalidade é coberta por `/api/v1/prices`.
- Busca indexada não encontrou consumidor da rota.
- Candidato à remoção física após fechar prova de consumidores/imports, preservando `quotes_service` interno apenas onde compatível com a nova política de preço live.

### Proventos — CANÔNICO DB-FIRST

- Router: `backend/app/routers/proventos.py`.
- Prefixo efetivo: `/api/v1/portfolios/{portfolio_id}/proventos`.
- Frontend usa `frontend/src/services/proventosService.ts` nessa superfície.
- Contrato deriva direitos sob demanda de `asset_dividends` e posição histórica persistidos.
- Provider não participa do request.

### Dividends — COMPATIBILIDADE LEGADA EM AUDITORIA

- Router: `backend/app/routers/dividends.py`.
- Endpoint: `GET /api/v1/portfolios/{portfolio_id}/dividends`.
- Frontend canônico usa `/proventos`.
- O endpoint é read-only e projeta direitos a partir de dados persistidos.
- Não remover apenas por ausência no frontend; confirmar consumidores externos.

### Histórico de preços — CANÔNICO DB-FIRST

- Router: `backend/app/routers/prices.py`.
- Endpoint: `GET /api/v1/prices/{ticker}/history`.
- Leitor: `price_history_service.get_price_history`.
- O request é somente leitura do banco e não consulta provider nem dispara backfill.
- Gate estrutural impede regressão.

### Performance — READ-ONLY APÓS CORREÇÃO

- O antigo `POST /api/v1/performance/{portfolio_id}/evolution/backfill` foi removido da API pública.
- Serviços internos de rebuild permanecem disponíveis para operação explícita.
- Gate impede reintrodução da porta HTTP.

### Transactions — CRUD CANÔNICO, SYNC EXTERNO DESACOPLADO

- CRUD de transações permanece funcional.
- Onboarding de mercado e backfill de Proventos deixaram de ser disparados após POST/PATCH.
- Permanecem apenas efeitos locais derivados.
- Gate impede reintrodução de pipeline/provider no router.

### Positions — CANÔNICO DB-FIRST APÓS CORREÇÃO

- `refresh=true` e `update_quotes_for_portfolio` foram removidos dos GETs financeiros.
- A superfície lê somente dados persistidos.
- Gate impede regressão.

### Rentabilidade — CANÔNICO DB-FIRST

- Expõe somente GETs de KPIs, resultados por ativo/classe, benchmarks persistidos e reconciliação.
- Nenhum provider participa dos requests.

### Assets — ALTA PRIORIDADE / DESVIO PROVIDER PARCIAL

`backend/app/routers/assets.py` mistura leitura local com chamadas externas. Pela nova regra, a classificação anterior de “descoberta/provider interativa” deixa de ser aceita como fronteira definitiva.

**Alinhado/DB-first:**
- `GET /api/v1/assets/`;
- `GET /api/v1/assets/search`;
- `POST /api/v1/assets/` somente quando trabalhar com catálogo já persistido.

**Requer revisão imediata:**
- `GET /api/v1/assets/{ticker}/detail` porque `current_price` ainda usa fachada live;
- `GET /api/v1/assets/suggest` porque consulta provider para descoberta;
- `GET /api/v1/assets/tesouro/search` porque consulta provider;
- `GET /api/v1/assets/tesouro/price` porque consulta provider;
- `GET /api/v1/assets/quote/{ticker}` porque consulta provider e mistura múltiplas fontes.

Destino esperado:

- catálogo, sugestões, Tesouro e metadados devem vir do banco alimentado pelo bootstrap;
- somente preço intraday/fechamento pode permanecer live;
- qualquer endpoint de preço live deve ter semântica explícita, persistência e não ser usado diretamente por cálculos financeiros.

### Debug — CONDICIONAL/ADMIN SENSÍVEL

- Condicionado por `APP_DEBUG` ou `ADMIN_SECRET` no `app.main` e protegido por secret/rate limiting.
- Não classificado como legado neste momento.

## Frontend confirmado

- `/carteira/proventos` usa API canônica de Proventos.
- `/carteira/metas` permanece fora da estabilização até #246/#57.
- `/metas` e `/irpf` são redirects de compatibilidade explícitos.
- Não há rota de Análise no frontend protegido.
- `performanceService.ts` não expõe backfill.

## Prioridades da próxima rodada

1. **P0:** revisar `assets`, `quotes_service`, scheduler e entrypoint para garantir provider recorrente apenas em intraday/fechamento.
2. **P0:** mapear o bootstrap inicial necessário para catálogo, históricos, Proventos, eventos, Tesouro, benchmarks e câmbio.
3. **P1:** fechar prova de consumidores do router placeholder `quotes` e removê-lo se seguro.
4. **P1/P2:** revisar `portfolios`, `admin`, `irpf` e `class_targets` por mutações/aliases redundantes.
5. **P2:** decidir destino de `dividends` após prova de consumidores externos.

## Regra de remoção

Nenhum endpoint de compatibilidade será removido somente por não aparecer no frontend. Para remoção segura, exigir busca de consumidores, revisão de testes/documentação, classificação na #247, decisão explícita e gate de regressão quando aplicável.
