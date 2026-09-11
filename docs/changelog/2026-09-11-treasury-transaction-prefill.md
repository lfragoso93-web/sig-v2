# 2026-09-11 - Autopreenchimento de Tesouro no lancamento

## Contexto

Com o seed de Tesouro Direto, o sistema ja possui catalogo persistido e serie de
precos. O modal de lancamento ainda deixava o usuario preencher manualmente
campos estruturais do titulo, como indexador e vencimento, mesmo quando o ativo
ja era identificado no catalogo.

## Alteracoes

- O modal de lancamento reconhece correspondencia exata de Tesouro por nome,
  ticker ou slug.
- Ao identificar o titulo, o modal aplica automaticamente a sugestao do catalogo.
- O preenchimento automatico cobre nome, indexador, vencimento e busca do PU da
  data informada.
- A regra vale para compra e venda.
- Indexador e vencimento ficam derivados do titulo selecionado quando ha slug
  ativo, reduzindo divergencia entre lancamento e catalogo seedado.

## Validacao

- `npm run typecheck`
  - Resultado: sucesso.
- `npx vitest run legacyMutationModalsAbsence.test.ts hooks/marketLookupErrors.test.ts --pool threads --maxWorkers 1 --no-file-parallelism`
  - Resultado: `8 passed`.
- `npm run build`
  - Resultado: sucesso.

## Observacoes

O PU continua editavel pelo usuario. A busca automatica usa o endpoint persistido
de Tesouro para a data da operacao.
