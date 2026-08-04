# Política canônica de IRRF em renda variável

## Objetivo

Este documento descreve o módulo read-only `irpf_withholding_policy.py`, criado
na Issue #56 para separar a retenção na fonte da apuração mensal do imposto.

## Regras implementadas

### Operações comuns

- base de cálculo: valor bruto das vendas da competência;
- alíquota de IRRF: 0,005%;
- arredondamento: centavos com `ROUND_HALF_UP`.

### Day Trade

- base de cálculo: resultado líquido positivo da modalidade na competência;
- alíquota de IRRF: 1%;
- prejuízo ou resultado zero não gera retenção;
- arredondamento: centavos com `ROUND_HALF_UP`.

## Fronteira arquitetural

O módulo calcula somente a retenção bruta esperada. Ele não:

- deduz IRRF do imposto mensal devido;
- transporta saldo de IRRF entre competências;
- aplica DARF mínima;
- persiste valores;
- altera `calc_ganhos_capital`;
- altera endpoints, schemas ou frontend.

A compensação do IRRF deverá consumir explicitamente a apuração mensal canônica
em um bloco próprio, sem misturar retenção, prejuízos e DARF em uma única função.

## Fontes normativas

A política segue a orientação publicada pela Receita Federal para renda variável:

- operações comuns: retenção de 0,005% sobre o valor da venda;
- Day Trade: retenção de 1% sobre o resultado líquido positivo das operações da
  modalidade realizadas no mesmo dia.

## Testes protegidos

- base e alíquota de operações comuns;
- base e alíquota de Day Trade;
- ausência de retenção em prejuízo Day Trade;
- arredondamento determinístico;
- rejeição de valor de venda negativo.
