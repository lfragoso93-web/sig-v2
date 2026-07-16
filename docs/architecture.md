# Arquitetura — SGI v2

> Última atualização: 14/07/2026

Este documento descreve a arquitetura atual do SGI v2 após a migração para o modelo **DB-first**.

---

## Objetivo

O sistema deve calcular patrimônio, resultado, proventos e rentabilidade com base em dados persistidos e auditáveis. Provedores externos servem para preencher lacunas do banco, não para responder diretamente a cada cálculo de carteira.

---

## Fluxo principal

```text
CSV / lançamentos manuais
        ↓
transactions
        ↓
asset catalog
        ↓
coverage auditor
        ↓
price gap sync
        ↓
asset_prices + benchmarks + dividends + treasury history
        ↓
portfolio snapshots
        ↓
TWR daily chain
        ↓
canonical KPIs
        ↓
Resumo / Patrimônio / Rentabilidade / Dashboard
```

---

## Princípios

### 1. DB-first

Serviços de cálculo financeiro leem apenas o banco. Eles não devem chamar provedores externos durante a execução de snapshots, KPIs ou telas.

### 2. Sincronização antes do cálculo

Dados externos são coletados por jobs de sincronização, pelo scheduler ou pelo comando `full_market_rebuild`.

### 3. Idempotência

Executar uma manutenção duas vezes deve produzir o mesmo estado lógico, sem duplicar preços, dividendos ou snapshots.

### 4. Conexões curtas

Chamadas HTTP não devem manter sessões ou transações do PostgreSQL abertas. O fluxo recomendado é:

```text
ler estado mínimo
fechar sessão
consultar provedor
abrir sessão curta
persistir em lote
commit
```

### 5. Qualidade explícita

Quando faltam preços ou os retornos dependem de fluxos inferidos, isso deve aparecer nos campos:

- `has_partial_prices`
- `return_is_estimated`

---

## Módulos centrais

| Módulo | Responsabilidade |
|---|---|
| `transactions` | Fonte contábil dos lançamentos do usuário |
| `assets` | Catálogo canônico e metadados de provedor |
| `asset_prices` | Histórico diário persistido de preços |
| `asset_price_coverage_service` | Auditoria de cobertura por ativo |
| `asset_price_gap_sync_service` | Preenchimento de lacunas históricas |
| `asset_price_global_backfill_service` | Orquestração global de catálogo e preços |
| `dividend_*` | Eventos canônicos e materialização por carteira |
| `treasury_price_history_service` | Histórico dedicado de Tesouro Direto |
| `portfolio_snapshot_twr_service` | Snapshots DB-only com fluxos, proventos e TWR |
| `full_market_rebuild_service` | Manutenção operacional completa |

---

## Dados canônicos

O SGI mantém dados canônicos para evitar divergência entre páginas.

```text
Transações
 + Preços históricos
 + Proventos materializados
 + Benchmarks
 + Tesouro
        ↓
Snapshot diário
        ↓
KPIs canônicos
```

As páginas Resumo, Patrimônio e Rentabilidade devem consumir os mesmos contratos financeiros, mudando apenas a forma de apresentação.

---

## Scheduler diário

A ordem recomendada é:

```text
20:20 — sincronização incremental de ativos
20:45 — auditoria global e gap sync
20:50 — benchmarks e Tesouro
20:55 — proventos
21:00 — snapshots e TWR
```

Os horários podem ser ajustados, mas a regra deve ser mantida: **sincronizar dados antes de reconstruir snapshots**.

---

## Fluxo manual completo

```bash
python -m app.cli.full_market_rebuild
```

Etapas:

1. Catálogo e preços por lacuna.
2. Tesouro Direto.
3. Benchmarks.
4. Proventos.
5. Snapshots TWR.
6. Auditoria final.

O comando continua executando etapas mesmo que uma delas registre erro interno, mas o resultado final deve ficar `ok=false` quando houver falhas relevantes.

---

## Tipos de ativos

| Classe | Tratamento |
|---|---|
| Ações, ETFs nacionais e BDRs | Histórico em `asset_prices` via fonte principal |
| FIIs | Histórico em `asset_prices` via rota dedicada |
| Stocks e ETFs internacionais | Fonte internacional, com fallback controlado |
| Cripto | Em revisão para roteamento definitivo |
| Tesouro Direto | Serviço dedicado de Tesouro |
| Renda Fixa | Motor interno, sem cotação de mercado genérica |

---

## Estados de cobertura

| Estado | Significado |
|---|---|
| `COMPLETE` | Histórico cobre o intervalo necessário |
| `MISSING` | Nenhum preço encontrado |
| `PARTIAL_START` | Falta histórico antes do primeiro preço salvo |
| `STALE` | Histórico está desatualizado na cauda |
| `PARTIAL_BOTH` | Faltam início e cauda |
| `NO_MARKET_QUOTE` | Classe não depende de cotação externa |
| `DEDICATED_PROVIDER` | Classe possui serviço próprio |
| `MISSING_ASSET` | Transação sem ativo correspondente no catálogo |

`PARTIAL_START` pode ser aceitável quando o provedor já retornou todo o histórico disponível. Nesse caso, `provider_status=HISTORY_START_EXHAUSTED` impede repetir a mesma busca.

---

## Pendências arquiteturais conhecidas

- Resolver `pricing_asset_id` para tickers fracionários sem duplicar histórico.
- Fazer snapshots de Tesouro consumirem diretamente o histórico dedicado.
- Finalizar roteamento de cripto e Tesouro após validação completa de cobertura do provedor.
- Evoluir locks em memória para locks distribuídos caso haja múltiplas réplicas.
- Consolidar provider router definitivo por capacidade.
