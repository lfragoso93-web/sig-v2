# RESUME — SIG v2

Estado atual do projeto em 15 Jun 2026. Ponto de partida para a proxima sessao.

---

## Estado Geral

| Item | Status |
|---|---|
| Backend FastAPI | ✅ Rodando — async em todos os servicos |
| Frontend React/Vite | ✅ Compilando |
| Autenticacao | ✅ Zustand + JWT |
| Carteiras e Posicoes | ✅ Sprint 4 concluida |
| Cotacoes e Snapshots | ✅ Sprint 5 concluida |
| Proventos (backend) | ✅ Sprint 6 concluida |
| Proventos (frontend) | ✅ Sprint 6 concluida |
| Rentabilidade | 🔜 Sprint 7 — proxima |

---

## Ultimo commit

`docs(sprint6): atualizar CHANGELOG, ROADMAP e RESUME com frontend de Proventos`

---

## Arquivos alterados na Sprint 6

| Arquivo | Commit |
|---|---|
| `backend/app/services/dividend_backfill_service.py` | `73538f57` |
| `backend/app/services/proventos_service.py` | `75790b79` |
| `backend/app/routers/proventos.py` | `ff41314a` |
| `backend/app/routers/dividends.py` | `d2e7b5d5` |
| `frontend/src/services/proventosService.ts` | `c8ed7f85` |
| `frontend/src/hooks/useProventos.ts` | `a6b7ffef` |
| `frontend/src/pages/ProventosPage.tsx` | `670fc7bb` |

---

## Endpoints de Proventos

| Endpoint | Descricao |
|---|---|
| `GET /portfolios/{id}/proventos/summary` | KPIs: total_recebido, total_a_receber, total_12m, media_mensal_12m |
| `GET /portfolios/{id}/proventos` | Lista paginada (filtros: status, year, asset_type) |
| `GET /portfolios/{id}/proventos/historico-mensal` | Grid por ano/mes |
| `GET /portfolios/{id}/proventos/distribuicao` | Distribuicao % por ativo |
| `POST /portfolios/{id}/dividends/sync` | Sincronizacao manual — 202 Accepted |

---

## Pendencias tecnicas conhecidas

- `ProventosHistoricoTable.tsx` usa classes CSS legadas (`text-muted`, `border-light-border`) — a migrar para CSS vars nas proximas sprints
- `ProventosDonutChart` precisa de validacao com dados reais de distribuicao
- Nenhum teste automatizado escrito para o frontend ainda

---

## Proxima sprint — Sprint 7: Rentabilidade

**Objetivo:** calcular rentabilidade de forma util para decisao.

**Criterios de aceite:**
- Rentabilidade por ativo bate com transacoes e cotacoes
- Carteira mostra retorno total com e sem proventos
- Ativos vendidos continuam contribuindo para lucro realizado
- Tela nao quebra quando cotacao esta ausente

**Arquivos provaveis:**
- `backend/app/services/rentabilidade_service.py` — novo
- `backend/app/routers/rentabilidade.py` — novo
- `frontend/src/services/rentabilidadeService.ts` — novo
- `frontend/src/hooks/useRentabilidade.ts` — novo
- `frontend/src/pages/RentabilidadePage.tsx` — a implementar

---

## Decisoes de arquitetura consolidadas

- **AsyncSession** em todos os servicos e routers do backend
- **Dois niveis de provento:** `asset_dividends` (global) + `dividends` (carteira)
- **SKIP_TYPES:** CRIPTO, TESOURO_DIRETO, RENDA_FIXA ignorados no backfill
- **Calculo de quantity:** posicao liquida na data-ex via `Transaction(portfolio_id, ticker, date <= ex_date)`
- **net_value:** `total_value * 0.85` para JCP; `total_value` para os demais
- **Prefixo de rotas:** gerenciado pelo `main.py` — nao hardcodar `/api/v1` nos routers
- **Tipos de ativo:** fonte unica em `asset_types.py`
