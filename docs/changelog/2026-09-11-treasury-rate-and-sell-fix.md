# 2026-09-11 - Taxa do Tesouro e venda canonica

## Contexto

O modal de lancamento passou a preencher vencimento e PU do Tesouro, mas a taxa
continuava vazia. Em paralelo, vendas ainda podiam falhar com quantidade
insuficiente quando compras historicas estavam em outra caixa/formato de ticker.

## Alteracoes

- O parser oficial do Tesouro Transparente passou a extrair taxa diaria quando
  presente no CSV.
- O seed historico passa a persistir a taxa em `asset_prices.open` para linhas
  de Tesouro.
- O endpoint `/assets/tesouro/price` passou a devolver `rate`.
- Foi criado serviço de leitura enriquecida de taxa do Tesouro, mantendo o router
  sem dependencia direta de provider.
- O frontend passou a consumir `rate` em `useTreasuryPrice` e preencher
  `Taxa (% a.a.)` automaticamente.
- A validacao de venda em transacoes compara ticker em lowercase apos resolver o
  Tesouro pelo catalogo.

## Validacao

- `pytest tests/integrations/test_tesouro_transparente.py tests/test_assets_router_provider_boundary.py tests/test_transaction_write_service.py`
  - Resultado: `16 passed`.
- `python -m compileall app`
  - Resultado: sucesso.
- `npm run typecheck`
  - Resultado: sucesso.
- `npx vitest run hooks/marketLookupErrors.test.ts --pool threads --maxWorkers 1 --no-file-parallelism`
  - Resultado: `5 passed`.
- `npm run build`
  - Resultado: sucesso.

## Observacoes

Bases ja seedadas podem nao ter `asset_prices.open` preenchido. Ate o proximo
seed historico, o endpoint tenta buscar a taxa oficial diretamente no Tesouro
Transparente quando ela nao existir no banco.
