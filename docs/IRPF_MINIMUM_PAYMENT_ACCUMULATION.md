# Acumulação configurável de pagamento mínimo do IRPF

## Objetivo

Este documento descreve o módulo read-only
`irpf_minimum_payment_accumulation.py`, criado na Issue #56 para separar a
acumulação de imposto líquido da apuração de resultado, prejuízos e IRRF.

## Contrato atual

O módulo recebe explicitamente:

- competência mensal;
- imposto líquido da competência;
- saldo acumulado inicial;
- limite mínimo de pagamento.

O comportamento é:

1. arredondar valores monetários em centavos com `ROUND_HALF_UP`;
2. somar imposto líquido do mês ao saldo acumulado;
3. manter o saldo quando o total estiver abaixo do limite configurado;
4. expor o total como pagamento devido quando atingir ou superar o limite;
5. zerar o saldo acumulado após o pagamento devido;
6. ordenar competências cronologicamente na avaliação em lote.

## Decisão arquitetural

O valor normativo do limite não está fixado no módulo. Ele é um parâmetro
obrigatório para impedir que uma regra fiscal não verificada seja incorporada
silenciosamente ao runtime.

Enquanto o limite oficial e seu tratamento operacional não forem validados em
fonte normativa vigente, este módulo não deve ser conectado a endpoints,
relatórios ou persistência.

## Fora do escopo deste corte

- valor padrão do limite mínimo;
- integração à apuração anual;
- geração ou emissão de DARF;
- vencimento e calendário útil;
- juros e multa;
- persistência de saldo entre anos;
- alteração de `calc_ganhos_capital`;
- alteração de endpoints, schemas ou frontend.

## Testes protegidos

- valor abaixo do limite é acumulado;
- atingimento exato do limite gera pagamento;
- valor acima do limite gera pagamento integral;
- saldo é transportado cronologicamente;
- saldo é zerado após pagamento;
- valores e limites inválidos são rejeitados.
