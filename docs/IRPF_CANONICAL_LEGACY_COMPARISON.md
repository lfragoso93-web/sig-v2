# Comparação controlada entre IRPF canônico e legado

## Objetivo

Este documento descreve o comparador read-only criado na Issue #56 para medir,
sem alterar o runtime de produção, as diferenças entre:

- `assess_annual_common_operations`, baseado em baixas canônicas; e
- `calc_ganhos_capital`, consumidor fiscal legado.

O comparador não define qual saída deve ser exposta ao usuário. Ele produz
evidência estruturada para a migração posterior.

## Escopo atual

A comparação considera somente operações comuns. Day Trade, IRRF, DARF mínima,
persistência de saldos e contratos públicos permanecem fora deste corte.

Para cada competência mensal são comparados:

- PnL realizado de Swing Trade/operações comuns;
- base tributável;
- imposto devido de Swing Trade/operações comuns;
- grupos fiscais presentes no caminho canônico.

## Classificações

- `match`: valores e presença mensal coincidem;
- `legacy_missing_month`: o canônico possui competência sem equivalente legado;
- `canonical_missing_month`: o legado possui competência sem equivalente canônico;
- `class_segregation`: a divergência envolve BDR, ETF, FII/Fiagro ou mais de um grupo;
- `stock_exemption`: o canônico aplicou isenção mensal de ações;
- `loss_carryforward`: o canônico consumiu prejuízo acumulado do mesmo grupo;
- `unknown`: divergência ainda não explicada pelas causas conhecidas.

As classificações podem coexistir na mesma competência.

## CLI operacional

A comparação pode ser executada dentro do container backend sem criar endpoint
público:

```bash
python -m app.cli.irpf_compare_legacy --portfolio-id 1 --year 2024
```

O comando imprime um documento JSON com o contrato:

- `schema_version`: `irpf-canonical-legacy-comparison.v1`;
- identificação da carteira e ano fiscal;
- indicador `has_divergences`;
- totais de meses comparados, equivalentes e divergentes;
- comparação mensal detalhada e classificações conhecidas.

Para uso em automação, `--fail-on-divergence` retorna exit code `2` quando o
relatório contém divergências. Falhas operacionais ou argumentos inválidos
retornam exit code `1`; execução válida sem essa condição retorna `0`.

A sessão de banco é encerrada com rollback explícito. A CLI não grava artefatos,
não altera tabelas e não persiste saldos fiscais.

## Invariantes arquiteturais

1. O comparador é read-only.
2. Nenhum endpoint ou schema público é alterado.
3. O motor canônico continua consumindo `CanonicalRealizedDisposal`.
4. O legado permanece inalterado durante a coleta de evidências.
5. Divergências entre classes não são ocultadas por consolidação anual.
6. A substituição do runtime só deve ocorrer após análise das divergências reais.
7. O JSON da CLI é versionado e adequado para evidência operacional.

## Próximos passos

1. executar a CLI contra carteiras reais controladas;
2. consolidar divergências por causa, mês e classe;
3. corrigir causas não explicadas antes da migração;
4. somente então planejar a troca gradual do consumidor de produção.
