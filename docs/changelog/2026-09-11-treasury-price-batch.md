# 2026-09-11 - Busca em lote de precos do Tesouro

## Contexto

O backfill canonico de rentabilidade ja reutilizava a projecao de posicoes e os
caches de catalogo do Tesouro, mas ainda consultava o preco historico de cada
posicao de Tesouro individualmente em cada data.

## Alteracoes

- Adicionada busca em lote dos precos do Tesouro em ou antes da data alvo.
- A correcao canonica de Tesouro passou a coletar os tickers elegiveis antes de
  aplicar a correcao de mercado.
- Mantida a funcao pontual `_treasury_price_at_or_before` como wrapper de
  compatibilidade.
- Adicionados testes cobrindo cache, aliases canonicos e chamada em lote.

## Validacao

- `pytest tests/test_portfolio_canonical_treasury_correction.py tests/services/test_portfolio_canonical_valuation_service.py tests/test_portfolio_snapshot_canonical_twr_service.py`
  - Resultado: `16 passed`.
- `python -m compileall app`
  - Resultado: sucesso.
- Medicao local na carteira `15`:
  - `days_back=30`
  - `23 snapshots`
  - `1,428s`

## Observacoes

A regra de precificacao nao mudou: o sistema continua usando o ultimo preco
oficial persistido em ou antes da data de avaliacao, sem interpolacao e sem
cotacao futura.
