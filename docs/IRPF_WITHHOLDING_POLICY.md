# Política canônica de IRRF em renda variável

## Objetivo

Este documento descreve os módulos read-only de IRRF criados na Issue #56 para
separar retenção, compensação e imposto líquido da apuração mensal bruta.

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

## Compensação mensal

O módulo `irpf_withholding_compensation.py` recebe imposto bruto, IRRF do mês e
saldo anterior do mesmo bucket. Ele devolve:

- IRRF usado na competência;
- saldo final de IRRF;
- imposto líquido após retenção.

Os buckets `common` e `day_trade` são preservados explicitamente e nunca se
compensam entre si.

## Integração anual read-only

`irpf_annual_integrated_assessment_service.py` passou a:

1. calcular IRRF comum a partir das vendas brutas do excedente Swing;
2. calcular IRRF Day Trade a partir do resultado mensal positivo;
3. transportar saldo de IRRF apenas dentro do mesmo bucket;
4. expor imposto bruto e líquido anual por modalidade;
5. expor saldos finais segregados de IRRF;
6. manter a apuração paralela sem persistência e sem troca de runtime.

## Fronteira arquitetural

Ainda não fazem parte deste corte:

- DARF mínima e acumulação de imposto abaixo do limite;
- persistência de saldos fiscais;
- alteração de `calc_ganhos_capital`;
- alteração de endpoints, schemas ou frontend;
- geração de guia de pagamento.

A retenção não altera prejuízos fiscais: compensação de prejuízo e compensação de
IRRF permanecem etapas independentes do pipeline.

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
- rejeição de valores negativos;
- compensação total e parcial do imposto;
- transporte de saldo de IRRF;
- preservação dos buckets comum e Day Trade;
- integração anual de imposto bruto, líquido e saldos finais.
