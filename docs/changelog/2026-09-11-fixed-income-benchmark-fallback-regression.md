# 2026-09-11 - Correcao de fallback de Renda Fixa por benchmark recente

## Contexto

Depois da otimizacao de valuation, Renda Fixa voltou a exibir algumas posicoes
com valor atual igual ao aplicado. O caso visivel foi `LIG LIQUIDEZ`, que ficou
com resultado zerado na tela Patrimonio.

## Causa

Uma aplicacao CDI recente sem taxa posterior ao dia de compra propagava
`IncompleteBenchmarkCoverageError` para o valuation completo de Renda Fixa. A
camada de tela interpretava isso como indisponibilidade da classe inteira e
voltava todos os produtos para principal.

## Mudancas

- Aplicacao CDI/SELIC sem periodo coberto posterior ao proprio start usa fator
  `1`, sem derrubar as demais aplicacoes.
- Posicoes e Resumo tentam usar a ultima data coberta do benchmark antes de
  degradar para principal.
- Testes cobrem aplicacao CDI nova sem taxa posterior e fallback por ultima data
  coberta.

## Validacao

- Testes focados: `8 passed`.
- Carteira `15`: `LIG LIQUIDEZ` validada com aplicado `R$ 121,14`, valor atual
  `R$ 127,20` e resultado `R$ 6,06`.
- Cache local de portfolio/rentabilidade da carteira `15` invalidado.
