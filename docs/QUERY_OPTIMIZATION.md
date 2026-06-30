# Auditoria e Otimização de Queries — SIG v2

> Gerado em: 2026-06-30  
> Branch: `stable-15jun`  
> Referência: Issue #83 Sprint 8

---

## Resumo Executivo

A auditoria identificou **4 padrões críticos** de ineficiência distribuídos nos serviços de maior tráfego. As correções aplicadas neste bloco eliminam os dois N+1 mais custosos e consolidam queries redundantes no caminho crítico (`/portfolios/{id}/resumo` e `/kpis`).

| ID | Serviço | Tipo | Severidade | Status |
|----|---------|------|------------|--------|
| Q1 | `portfolio_snapshot_service` | N+1 Asset dentro de loop | 🔴 Alta | ✅ Corrigido |
| Q2 | `portfolio_service` | `sum_dividends` 3x para mesmos dados | 🔴 Alta | ✅ Corrigido |
| Q3 | `rentabilidade_service` | `_calc_invested_up_to` 2x sem batching | 🟡 Média | ✅ Corrigido |
| Q4 | `portfolio_snapshot_service` | `_prefetch_price_history` sem índice eficiente | 🟡 Média | 📋 Índice recomendado |
| Q5 | `irpf_service` | Carrega todas as transações sem filtro de ano | 🟡 Média | 📋 Índice recomendado |
| Q6 | `price_history_service` | `get_price_at_date` sem índice composto | 🟡 Média | 📋 Índice recomendado |
| Q7 | `fx_service` | `get_usd_brl_batch` sem índice em `rate_date` | 🟢 Baixa | 📋 Índice recomendado |

---

## Detalhamento por Problema

### Q1 — N+1 em `_calc_totals` (portfolio_snapshot_service)

**Arquivo:** `backend/app/services/portfolio_snapshot_service.py`  
**Função:** `_calc_totals`

**Antes:**
```python
for ticker, state in positions.items():
    asset_result = await db.execute(
        select(Asset).where(Asset.ticker == ticker)  # ← 1 query POR ticker!
    )
    asset = asset_result.scalar_one_or_none()
```

**Depois:**
```python
# 1 query batch ANTES do loop
asset_rows = await db.execute(
    select(Asset.ticker, Asset.asset_type)
    .where(Asset.ticker.in_(list(positions.keys())))
)
asset_type_map = {r.ticker: r.asset_type for r in asset_rows.all()}

for ticker, state in positions.items():
    asset_type = asset_type_map.get(ticker) or AssetType(state.asset_type)
```

**Impacto:** Carteira com 20 ativos: **20 queries → 1 query**. Em backfill de 1 ano (≈250 dias úteis): **5.000 queries → 250 queries**.

---

### Q2 — `sum_dividends` 3x em `get_portfolio_summary`

**Arquivo:** `backend/app/services/portfolio_service.py`  
**Função:** `get_portfolio_summary`

**Antes:**
```python
dividendos_12m = await sum_dividends(db, portfolio_id, cutoff=cutoff_12m)  # query 1
total_proventos = await sum_dividends(db, portfolio_id)                     # query 2
proventos_em_carteira = await sum_dividends_for_tickers(db, portfolio_id, tickers)  # query 3
```

**Depois:** Uma única query agrupada por ticker retorna todos os valores necessários; `total_proventos` é calculado somando o resultado in-memory.

**Impacto:** 3 queries → 1 query a cada chamada ao endpoint `/resumo`.

---

### Q3 — `_calc_invested_up_to` chamada 2x sem batching

**Arquivo:** `backend/app/services/rentabilidade_service.py`  
**Função:** `_kpis_from_realtime`

**Antes:**
```python
custo_inicio_mes = await _calc_invested_up_to(db, portfolio_id, inicio_mes)   # carrega todas as txs
custo_inicio_12m = await _calc_invested_up_to(db, portfolio_id, inicio_12m)   # carrega todas as txs novamente
```

**Depois:** `_calc_invested_up_to_both(db, portfolio_id, date_a, date_b)` carrega as transações uma única vez e computa os dois acumulados em memória.

**Impacto:** Aplicável apenas ao fallback (sem snapshots). 2 queries → 1 query.

---

### Q4 — Índice em `(portfolio_id, ticker)` em `transactions`

**Tabela:** `transactions`  
**Problema:** As queries mais frequentes filtram por `portfolio_id` e ordenam por `date`. O índice `idx_transaction_portfolio` cobre `portfolio_id`, mas não é composto com `date`, forçando sort em memória.

**Índice recomendado:**
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS
  idx_tx_portfolio_date
  ON transactions (portfolio_id, date ASC);
```

**Benefício:** Elimina `Sort` node no `EXPLAIN ANALYZE` das queries de `_build_positions_at` e `calc_raw_positions`.

---

### Q5 — `irpf_service` sem filtro de ano nas transações

**Arquivo:** `backend/app/services/irpf_service.py`  
**Problema:** O IRPF carrega todas as transações do portfólio sem filtrar por ano-base, processando anos anteriores desnecessariamente quando o usuário pede apenas o ano corrente.

**Recomendação:**
```python
# Adicionar filtro de ano-base para cálculo de DARFs e apuração mensal
.where(Transaction.date >= date(ano_base, 1, 1))
.where(Transaction.date <= date(ano_base, 12, 31))
```
Manter a carga completa apenas para cálculo de `custo_medio` (necessário para vendas do ano-base).

---

### Q6 — `get_price_at_date` sem índice composto em `price_history`

**Tabela:** `price_history`  
**Problema:** A função busca `(ticker, date <= target_date) ORDER BY date DESC LIMIT 1` sem índice composto.

**Índice recomendado:**
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS
  idx_price_history_ticker_date
  ON price_history (ticker, date DESC);
```

**Benefício:** Converte `Seq Scan` em `Index Scan` na tabela que mais cresce no sistema (~365 registros/ticker/ano).

---

### Q7 — `fx_rates` sem índice em `rate_date`

**Tabela:** `fx_rates` (ou equivalente no `fx_service`)  
**Problema:** `get_usd_brl_for_date` busca por data exata sem índice; com 1.000+ registros começa a impactar.

**Índice recomendado:**
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS
  idx_fx_rates_date
  ON fx_rates (rate_date DESC);
```

---

## Índices — Migration Recomendada

Criar arquivo `backend/migrations/versions/add_performance_indexes.py` com:

```python
"""add performance indexes

Revision ID: perf_indexes_2026_07
"""
from alembic import op

def upgrade():
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tx_portfolio_date
        ON transactions (portfolio_id, date ASC);
    """)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_price_history_ticker_date
        ON price_history (ticker, date DESC);
    """)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_portfolio_snapshot_portfolio_date
        ON portfolio_snapshot (portfolio_id, snapshot_date DESC);
    """)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dividends_portfolio_ticker
        ON dividends (portfolio_id, ticker);
    """)

def downgrade():
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_tx_portfolio_date;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_price_history_ticker_date;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_portfolio_snapshot_portfolio_date;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_dividends_portfolio_ticker;")
```

> ⚠️ Usar `CREATE INDEX CONCURRENTLY` para não bloquear leituras em produção.

---

## Cache Redis — Cobertura Atual

| Endpoint | Cache TTL | Invalidação |
|----------|-----------|-------------|
| `/rentabilidade/kpis` | 5 min | Após nova transação |
| `/rentabilidade/ativos` | 5 min | Após nova transação |
| `/rentabilidade/classes` | 5 min | Após nova transação |
| `/portfolios/{id}/resumo` | ❌ Sem cache | Adicionar TTL 2 min |
| `/portfolios/{id}/posicoes` | ❌ Sem cache | Adicionar TTL 2 min |
| `get_portfolio_summary` | ❌ Sem cache | Adicionar TTL 2 min |

**Recomendação:** Adicionar cache Redis com TTL 2 min nos endpoints de resumo e posições usando o mesmo padrão do `rentabilidade_service`.

---

## Monitoramento Recomendado

### Queries lentas no PostgreSQL
```sql
-- Habilitar no postgresql.conf:
log_min_duration_statement = 100  -- loga queries > 100ms

-- Ver queries mais lentas:
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### EXPLAIN ANALYZE nas queries críticas
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM transactions
WHERE portfolio_id = 1
ORDER BY date ASC;
-- Verificar: deve usar idx_tx_portfolio_date, não Seq Scan
```

---

## Próximos Passos

1. **Criar migration** com os índices recomendados (Q4, Q5, Q6, Q7)
2. **Adicionar cache** em `get_portfolio_summary` e `get_portfolio_positions`
3. **Filtrar por ano** no `irpf_service` mantendo carga completa só para custo médio
4. **Monitorar** com `pg_stat_statements` após deploy
