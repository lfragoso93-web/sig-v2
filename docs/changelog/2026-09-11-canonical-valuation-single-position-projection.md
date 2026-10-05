# 2026-09-11 - Valuation canonico com projecao unica de posicoes

## Contexto

O valuation canonico ainda executava `build_positions_at` duas vezes para a
mesma carteira/data: uma para a base patrimonial e outra para a correcao de
Tesouro. Em rebuilds historicos, essa duplicidade se multiplicava por cada dia
util.

## Mudancas

- `calculate_canonical_portfolio_totals` agora projeta posicoes uma unica vez.
- `_base_totals_without_dedicated_lookup` e `_treasury_correction_at_date`
  aceitam posicoes pre-carregadas.
- Chamadas isoladas dos helpers continuam compativeis, carregando posicoes
  internamente quando necessario.

## Validacao

- Testes focados de valuation canonico, snapshots e Tesouro: `15 passed`.
- Medicao local na carteira `15`: backfill canonico com `days_back=30` processou
  23 snapshots em 1,997s.
