# 2026-09-11 - Tesouro no modal com identidade canonica

## Contexto

Nos testes de usuario, o modal de lancamento de Tesouro ainda apresentava tres
problemas: campos parcialmente preenchidos, seletor compra/venda comprimido
pelas abas e falha de venda por quantidade insuficiente mesmo com posicao
existente.

## Alteracoes

- A tela de Tesouro passou a abrir o modal com `brapi_symbol`/ticker canonico.
- O prefill do modal ganhou `treasurySlug`.
- O modal inicializa `activeSlug`, indexador e vencimento quando o prefill ja
  identifica um Tesouro seedado.
- As abas do modal passaram a usar rolagem horizontal em vez de quebrar em
  varias linhas.
- O backend resolve o ticker de Tesouro no catalogo antes de validar venda ou
  persistir a transacao.
- A criacao de ativo auxiliar evita duplicidade por diferenca de caixa no ticker.

## Validacao

- `pytest tests/test_transaction_write_service.py tests/test_transaction_snapshot_invalidation_contract.py`
  - Resultado: `8 passed`.
- `python -m compileall app`
  - Resultado: sucesso.
- `npm run typecheck`
  - Resultado: sucesso.
- `npx vitest run legacyMutationModalsAbsence.test.ts hooks/marketLookupErrors.test.ts --pool threads --maxWorkers 1 --no-file-parallelism`
  - Resultado: `8 passed`.
- `npm run build`
  - Resultado: sucesso.
