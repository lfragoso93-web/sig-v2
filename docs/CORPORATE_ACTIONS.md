# Eventos corporativos

## Objetivo

Manter posições, custo médio, patrimônio e rentabilidade corretos após renomes, splits, grupamentos, bonificações, incorporações e conversões, sem alterar transações históricas.

## Estado atual

A primeira entrega implementa renomes simples de ticker na proporção 1:1.

Fluxo atual:

1. O provedor resolve o ticker antigo para o ticker atual.
2. O SGI registra um alias histórico.
3. É criado um evento `TICKER_CHANGE` vinculado à carteira.
4. O saldo imediatamente anterior à data efetiva é calculado.
5. Se houver saldo, o sistema cria uma saída técnica do ticker antigo e uma entrada técnica do ticker atual pelo mesmo custo médio.
6. O evento é marcado como aplicado.

## Regras

- Compras e vendas originais permanecem imutáveis.
- Venda total antes do renome não gera conversão.
- Venda parcial converte somente o saldo remanescente.
- Quantidade, custo total e preço médio são preservados.
- Operações posteriores à data efetiva devem usar o ticker atual.

## Idempotência

A chave lógica do evento considera carteira, ticker antigo, ticker atual e data efetiva.

As operações técnicas usam um marcador ligado ao ID do evento, impedindo dupla aplicação em reprocessamentos.

## Auditoria

Cada evento deve preservar:

- ticker antigo e atual;
- data efetiva;
- fonte do dado;
- carteira afetada;
- status;
- instante de aplicação;
- payload original normalizado.

## Próximos blocos

- Spike com HG Brasil.
- Splits e grupamentos.
- Bonificações e subscrições.
- Incorporações, fusões e conversões com proporção.
- Simulação antes da aplicação.
- Confirmação manual para eventos complexos.
- Rollback e reprocessamento controlado.
- Tela administrativa e auditoria operacional.

## Princípio arquitetural

O motor interno deve permanecer independente do provedor. Fontes externas alimentam eventos normalizados; o cálculo patrimonial e a aplicação das regras continuam sob responsabilidade do SGI.