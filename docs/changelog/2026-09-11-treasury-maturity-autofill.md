# 2026-09-11 - Vencimento automatico no Tesouro

## Contexto

O modal de lancamento passou a preencher o Tesouro a partir do catalogo, mas
consultas por nome comercial curto, como `TESOURO SELIC 2031`, ainda podiam
preencher indexador e PU sem preencher o vencimento.

## Alteracoes

- O modal aplica automaticamente uma sugestao unica do catalogo quando todos os
  termos digitados aparecem no titulo retornado.
- O endpoint de busca do Tesouro extrai vencimento de:
  - slugs compactos como `tesouro-selic-01032031`;
  - nomes oficiais com data `dd/mm/aaaa`;
  - nomes/slugs contendo data ISO `aaaa-mm-dd`.
- O teste estatico do modal foi atualizado para cobrir a busca unica compativel.
- O router de assets ganhou teste funcional para extracao de vencimento.

## Validacao

- `pytest tests/test_assets_router_provider_boundary.py tests/test_transaction_write_service.py`
  - Resultado: `10 passed`.
- `python -m compileall app`
  - Resultado: sucesso.
- `npm run typecheck`
  - Resultado: sucesso.
- `npx vitest run hooks/marketLookupErrors.test.ts --pool threads --maxWorkers 1 --no-file-parallelism`
  - Resultado: `5 passed`.
- `npm run build`
  - Resultado: sucesso.
