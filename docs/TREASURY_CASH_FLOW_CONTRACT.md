# Contrato de fluxo e IRRF do Tesouro Direto

## Limites

O evento global em `asset_dividends` representa somente o fluxo bruto por
unidade. Ele não possui `portfolio_id`, nem um valor líquido: duas aquisições
elegíveis do mesmo título podem ter alíquotas distintas de IRRF.

O projetor por carteira deriva, para cada lote de aquisição elegível:

```text
valor bruto + base tributável explícita + alíquota do lote
    -> IRRF retido na fonte + valor líquido
```

O IRRF não cria DARF, não é uma transação e não altera `asset_dividends` ou
`transactions`. A apresentação fiscal futura deve classificá-lo como retenção
na fonte já ocorrida; ela não pode enviá-lo aos grupos mensais de renda variável.

## Regra fail-closed

A base tributável por unidade de cada evento deve vir de uma fonte oficial ou de
um cálculo fiscal documentalmente reproduzível. O motor não pode deduzi-la do
PU, da taxa contratada, do valor líquido, nem de uma aproximação anual.

Para cupom adquirido entre datas de pagamento, essa base pode divergir do valor
bruto do cupom. Enquanto ela não estiver explicitamente disponível, o fluxo não
é materializável para fins de IRRF.

## Integração futura

- `RENDIMENTO` e `AMORTIZACAO` continuam sendo eventos globais canônicos;
- o direito exige a data de elegibilidade já exigida pelo leitor canônico;
- snapshots/TWR consomem o bruto uma única vez;
- o leitor fiscal recebe bruto, base tributável, IRRF e líquido por lote;
- CDB e outras modalidades de renda fixa não herdam este comportamento sem seu
  próprio contrato fiscal.
