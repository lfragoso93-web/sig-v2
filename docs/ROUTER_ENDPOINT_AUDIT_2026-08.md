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
- **EM AUDITORIA** — não classificado definitivamente até revisão de consumidores e contratos.

## Achados iniciais comprovados

### Análise de Carteira — PLACEHOLDER

- Router: `backend/app/routers/analysis.py`.
- Prefixo registrado: `/api/v1/analysis`.
- Comportamento atual: `501 Not Implemented`.
- A referência antiga a "Sprint 13" não representa a governança atual.
- A Issue #57 foi atualizada: Análise de Carteira está bloqueada e será redesenhada junto com Metas (#246).
- Não criar novos endpoints ou persistência antes do macroprojeto #246 + #57.

### Renda Fixa — PLACEHOLDER DE API

- Router: `backend/app/routers/fixed_income.py`.
- Prefixo registrado: `/api/v1/fixed-income`.
- Comportamento atual: `501 Not Implemented`.
- A referência antiga a "Sprint 14" é obsoleta.
- O domínio financeiro de Renda Fixa já possui valuation, contratos e serviços canônicos em outras superfícies; portanto esse placeholder não deve ser interpretado como ausência do domínio.
- Antes de remover ou substituir o router, confirmar se existe consumidor externo documentado.

### Proventos — CANÔNICO

- Router: `backend/app/routers/proventos.py`.
- Prefixo efetivo: `/api/v1/portfolios/{portfolio_id}/proventos`.
- Frontend usa `frontend/src/services/proventosService.ts` exclusivamente nessa superfície.
- Contrato deriva direitos sob demanda de `asset_dividends` e posição histórica.

### Dividends — COMPATIBILIDADE LEGADA EM AUDITORIA

- Router: `backend/app/routers/dividends.py`.
- Endpoint: `GET /api/v1/portfolios/{portfolio_id}/dividends`.
- Service: `backend/app/services/dividend_service.py`.
- Schema: `backend/app/schemas/dividend.py`, onde `DividendResponse` é alias de compatibilidade de `DividendRead`.
- Frontend canônico não usa essa superfície; usa `/proventos`.
- O endpoint é read-only e projeta direitos sob demanda, portanto não viola a arquitetura atual de persistência.
- Não remover ainda: falta comprovar ausência de consumidores externos e de testes/integrações fora do frontend principal.

### Performance backfill — OPERACIONAL EM AUDITORIA

- Router: `backend/app/routers/performance.py`.
- Endpoint mutável: `POST /api/v1/performance/{portfolio_id}/evolution/backfill`.
- Reconstrói snapshots consolidados e por classe.
- Apesar de exigir usuário autenticado e ownership da carteira, o endpoint dispara operação de reconstrução e precisa ser reconciliado com o gate #227, que exige operações reais explicitamente controladas/opt-in.
- Não alterar neste inventário; revisar consumidores, autorização e necessidade de exposição pública antes de qualquer mudança.

## Fronteiras já confirmadas no frontend

- `/carteira/proventos` usa `proventosService.ts` e a API `/portfolios/{id}/proventos`.
- `/carteira/metas` existe, mas o domínio `goals` permanece fora do escopo desta auditoria funcional até #246/#57.
- `/metas` e `/irpf` são redirects de compatibilidade explícitos.
- Não há rota de Análise atualmente registrada no frontend protegido.

## Próxima rodada da auditoria

1. Mapear todos os routers restantes registrados no `app.main`.
2. Identificar endpoints mutáveis/operacionais expostos em APIs de usuário comum.
3. Verificar consumidores frontend e testes para aliases/compatibilidades.
4. Revisar routers pequenos e duplicações sem tocar em `goals`.
5. Corrigir um grupo de achados comprovados por commit pequeno.

## Regra de remoção

Nenhum endpoint de compatibilidade será removido somente por não aparecer no frontend. Para remoção segura, exigir ao menos:

- busca de consumidores no repositório;
- revisão de testes e documentação;
- classificação na #247;
- decisão explícita de compatibilidade;
- teste de regressão que impeça reintrodução quando aplicável.
