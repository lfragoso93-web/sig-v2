# Finding CSV/B3 assistido - 08/09/2026

Usuario afetado: `lfragoso93@gmail.com`, carteira `Principal`
(`user_id=16`, `portfolio_id=15`).

## Evidencia operacional

- CSV real assistido persistiu 308 transacoes e 65 ativos distintos.
- Ativos B3 foram importados, mas Resumo/Posicoes retornavam erro e o frontend
  parecia vazio.
- Causa raiz: `IncompleteBenchmarkCoverageError` de CDI parcial para renda fixa
  em `2026-04-14..2026-09-08` propagava ate os endpoints de carteira.

## Correcao aplicada

- Resumo canonico/legado degrada renda fixa indisponivel para pendencia de
  cobertura, preservando totais e renderizacao dos ativos nao-RF.
- Posicoes preservam grupos nao-RF quando renda fixa nao pode ser precificada
  por cobertura parcial de benchmark.
- `RENDA_FIXA` entra em `assets_without_price` para deixar a pendencia
  auditavel sem mascarar readiness.

## Validacao local

- `.venv` focado: `24 passed`.
- Backend Docker reconstruido e `/health` 200.
- Runtime real da carteira 15: `total_patrimonio=20678.08`,
  `has_partial_prices=true`, 8 grupos e 34 posicoes abertas.

## Pendencias relacionadas

- Completar cobertura/precos faltantes para `AREA11`, `INTR`, `IVV`, `NVDA`,
  Tesouro/Renda+ especificos, `TFLO` e renda fixa.
- Investigar lacuna historica de `RBRF11` que impede rebuild integral de
  snapshots, sem bloquear a importacao transacional.
- Manter `ready_for_real_data=false` ate fechar cobertura/precos pendentes e os
  gates formais de liberacao.
