# Acumulação normativa de pagamento mínimo do IRPF

## Objetivo

Este documento descreve os módulos read-only
`irpf_minimum_payment_policy.py` e `irpf_minimum_payment_accumulation.py`,
criados na Issue #56 para separar a regra de pagamento mínimo da apuração de
resultado, prejuízos e IRRF.

## Regra normativa confirmada

O limite mínimo para utilização de DARF é de R$ 10,00. Quando o imposto apurado
em uma competência for inferior a esse valor, o montante deve ser adicionado ao
imposto de mesmo código de receita das competências subsequentes até que o total
atinja ou supere R$ 10,00. O pagamento ocorre no prazo da competência em que o
limite foi alcançado.

Para renda variável, o ReVar aplica o mesmo comportamento ao imposto mensal.

A constante canônica é:

```python
MINIMUM_DARF_PAYMENT_BRL = Decimal("10.00")
```

## Contrato de acumulação

O módulo recebe:

- competência mensal;
- imposto líquido da competência;
- saldo acumulado inicial;
- limite mínimo de pagamento.

O comportamento é:

1. arredondar valores monetários em centavos com `ROUND_HALF_UP`;
2. somar o imposto líquido do mês ao saldo acumulado;
3. manter o saldo quando o total estiver abaixo de R$ 10,00;
4. expor o total como pagamento devido quando atingir ou superar o limite;
5. zerar o saldo acumulado após o pagamento devido;
6. ordenar competências cronologicamente na avaliação em lote.

## Integração anual canônica

`irpf_annual_integrated_assessment_service.py` agrega, por competência, o imposto
líquido de operações comuns e Day Trade após compensação de IRRF. Essa soma é
avaliada contra o limite mínimo porque o recolhimento pertence ao mesmo código
de receita da renda variável.

A visão anual expõe:

- `minimum_payment_monthly`;
- `total_payment_due_brl`;
- `closing_accumulated_tax_brl`.

O saldo acumulado permanece explícito para continuidade futura. Ainda não há
persistência automática entre anos.

## Fontes normativas

- Lei nº 9.430/1996, art. 68 e § 1º;
- Instrução Normativa RFB nº 2.164/2023, art. 3º, § 2º;
- Manual do ReVar da Receita Federal.

## Fora do escopo deste corte

- geração ou emissão efetiva de DARF;
- vencimento e calendário útil;
- juros e multa;
- registro de pagamentos realizados;
- persistência de saldo entre anos;
- alteração de `calc_ganhos_capital`;
- alteração de endpoints, schemas ou frontend.

## Testes protegidos

- valor abaixo do limite é acumulado;
- atingimento exato do limite gera pagamento;
- valor acima do limite gera pagamento integral;
- saldo é transportado cronologicamente;
- saldo é zerado após pagamento;
- integração anual expõe saldo e pagamento devido;
- valores e limites inválidos são rejeitados.
