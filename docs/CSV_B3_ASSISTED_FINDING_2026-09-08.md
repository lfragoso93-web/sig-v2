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

## Bloco seguinte - preflight CSV e rebuild parcial

Correcao adicional aplicada:

- o rebuild canonico de snapshots agora interrompe na primeira lacuna real de
  preco persistido, preserva snapshots anteriores e registra a fronteira em log,
  em vez de propagar a excecao para a rotina de pos-importacao;
- o preflight financeiro do CSV passou a bloquear classes de mercado
  precificaveis sem catalogo/historico persistido (`ACAO`, `BDR`,
  `ETF_INTERNACIONAL`, `ETF_NACIONAL`, `FII`, `STOCK`);
- o preflight financeiro so roda quando o lote esta estruturalmente limpo, para
  nao misturar erros de formato com erros de cobertura.

Validacao adicional:

- testes focados CSV + snapshots: `49 passed`;
- backend Docker reconstruido e `/health` 200;
- rebuild limitado da carteira 15 parou sem excecao em `2026-08-10`, com
  pendencia explicita para `AREA11`, `INTR`, `IVV`, `NVDA` e `TFLO`;
- dry-run runtime na carteira 15 bloqueou `NVDA`, `IVV` e `AREA11` por
  historico de precos persistido indisponivel, mantendo `PETR4` valido.

## Bloco operacional - reparo de cobertura e snapshots

Execucoes operacionais controladas no banco local de validacao:

- `repair_market_price_gaps NVDA`: 6.949 linhas inseridas, primeira cotacao em
  `1999-01-22`;
- `repair_market_price_gaps TFLO`: 3.167 linhas inseridas, primeira cotacao em
  `2014-02-04`;
- `repair_market_price_gaps IVV`: cobertura confirmada com 6.614 linhas,
  primeira cotacao em `2000-05-19`;
- `repair_market_price_gaps INTR`: cobertura confirmada com 1.056 linhas,
  primeira cotacao em `2022-06-23`;
- `repair_market_price_gaps AREA11`: cobertura confirmada com 208 linhas,
  primeira cotacao em `2025-10-27`;
- `repair_market_price_gaps RBRF11`: cobertura ampliada para 2.492 linhas,
  primeira cotacao em `2017-09-15`.

Benchmark:

- seed macro oficial executado pelo wrapper `pre_prod_macro_seed.ps1`;
- evidencia: `artifacts/pre-prod-rebuild/20260908-195126/macro-seed.json`;
- CDI `2026-04-14..2026-09-08` validou como `complete`.

Correcao de runtime:

- a reconciliacao canonica por classe agora ajusta residuo de arredondamento de
  ate R$ 0,01 na maior classe e continua rejeitando divergencia material.

Validacao:

- testes focados de valuation/snapshot: `7 passed`;
- backend Docker reconstruido e `/health` 200;
- rebuild limitado da carteira 15 criou/atualizou 22 snapshots;
- carteira 15 passou a ter snapshots de `2026-08-10` a `2026-09-08`;
- Resumo canonico retornou `snapshot_date=2026-09-08`, 9 grupos e 35 posicoes.

## Bloco Tesouro - normalizacao e historico

Correcao aplicada:

- valuation canonico de Tesouro passa a resolver o simbolo no catalogo
  persistido e consultar o ticker exatamente como esta no banco, evitando falha
  por diferenca de caixa entre CSV/importacao e `assets`;
- leitura de preco atual persistido passou a ser case-insensitive, preservando a
  chave solicitada pelo chamador;
- leitura historica persistida e leitura historica em lote passaram a ser
  case-insensitive, incluindo o endpoint publico de historico;
- correcao canonica de Tesouro usa o ultimo preco oficial persistido ate a data
  do snapshot, sem chamar provider e sem inventar valor quando nao ha serie.

Validacao:

- testes focados: `11 passed`;
- backend Docker reconstruido;
- rebuild limitado da carteira 15 atualizou 22 snapshots;
- Resumo canonico da carteira 15 retornou `has_partial_prices=false`,
  `assets_without_price=[]`, `price_coverage_pct=100.0` e
  `snapshot_date=2026-09-08`;
- Posicoes exibiram `TESOURO-RENDA-MAIS-2060`, `TESOURO-RENDA-MAIS-2065` e
  `TESOURO-SELIC-01032031` com preco atual e valor de mercado;
- historico publico de `TESOURO-RENDA-MAIS-2065` retornou serie recente ate
  `2026-09-08`.
