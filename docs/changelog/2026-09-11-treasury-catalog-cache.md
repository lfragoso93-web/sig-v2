# 2026-09-11 - Cache de catalogo do Tesouro no backfill canonico

## Contexto

O valuation canonico ja reutilizava a projecao de posicoes, mas a correcao de
Tesouro ainda resolvia simbolo canonico e ticker persistido repetidamente para o
mesmo ativo durante rebuilds historicos.

## Mudancas

- `_treasury_correction_at_date` aceita caches opcionais de simbolo canonico e
  ticker persistido.
- `calculate_canonical_portfolio_totals` propaga esses caches para a correcao de
  Tesouro.
- `backfill_canonical_snapshots_with_returns` mantem os caches em memoria ao
  longo do loop diario.

## Validacao

- Testes focados de Tesouro, valuation canonico e snapshots: `15 passed`.
- Medicao local na carteira `15`: `days_back=30` processou 23 snapshots em
  1,751s.

## Observacao

O cache nao altera a politica de preco do Tesouro: a cotacao continua sendo
consultada por data no historico persistido oficial/exato.
