# 2026-09-14 - Gate agregado #216

## Decisao

O gate agregado #216 foi fechado consumindo a decisao da #226 e as evidencias
ja consolidadas de benchmarks e cambio.

## Evidencia consumida

- Benchmarks e cambio permanecem consolidados em documentacao e historico de
  certificacao.
- Proventos usa `asset_dividends` como unica persistencia canonica global.
- Direitos de carteira seguem calculados sob demanda, sem materializacao por
  carteira.
- A prova portfolio-scoped/idempotente de Proventos foi aceita na #226 como
  suficiente para promocao controlada.

## Fronteira operacional

Nao sera executado seed global de Proventos apenas por checklist historico.
Execucao global controlada so volta ao escopo se #158 encontrar necessidade
material nova durante a reconciliation.

## Proximo bloco

A Trilha A avanca para #158: promotion reconciliation minima e controlada sobre
SHA/dataset congelados, antes de #269, #284 e #227.
