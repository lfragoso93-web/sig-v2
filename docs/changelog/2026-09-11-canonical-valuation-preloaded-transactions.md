# 2026-09-11 - Valuation canonico com transacoes pre-carregadas

## Contexto

O rebuild consolidado de snapshots ainda fazia consultas repetidas de Renda
Fixa para cada dia util. Isso mantinha o fluxo correto, mas mais lento do que o
necessario em carteiras com historico longo.

## Mudancas

- `calculate_canonical_portfolio_totals` agora aceita uma lista opcional de
  transacoes pre-carregadas.
- `_fixed_income_totals_at_date` reutiliza essa lista quando disponivel e
  preserva o carregamento interno para chamadas pontuais.
- `backfill_canonical_snapshots_with_returns` passa a enviar as transacoes ja
  carregadas ao valuation diario.

## Validacao

- Testes focados de valuation canonico, Renda Fixa e snapshots: `16 passed`.
- Medicao local na carteira `15`: `days_back=30` processou 22 snapshots em
  2,858s.

## Observacao

A medicao local parou em 11/09/2026 por cobertura CDI ausente para
10/09/2026..11/09/2026. Esse comportamento permanece fail-closed e evita
calcular Renda Fixa indexada em benchmark sem base diaria certificada.
