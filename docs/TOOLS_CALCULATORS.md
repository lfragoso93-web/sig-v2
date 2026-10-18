# Ferramentas de simulação

Atualizado em 18/10/2026.

## Calculadora de rendimentos — primeira entrega da #359

A rota protegida `/carteira/ferramentas/rendimentos` oferece projeção isolada
com aporte inicial, aporte mensal, taxa efetiva anual e prazo de 1 a 600 meses.
O cálculo é puro no frontend, não chama API, não persiste dados e não lê nem
altera a carteira selecionada.

Premissas exibidas na tela:

- a taxa anual informada é efetiva e constante durante todo o horizonte;
- a taxa mensal equivalente é `(1 + taxa_anual)^(1/12) - 1`;
- o aporte inicial entra no mês zero;
- em cada mês, o saldo rende primeiro e o aporte mensal entra no fim do mês;
- não se aplicam impostos, inflação, tarifas, volatilidade nem datas de aporte.

Recorrência implementada: `saldo_m = saldo_(m-1) * (1 + taxa_mensal) + aporte_mensal`.
O total aportado é `aporte_inicial + aporte_mensal * meses`; o rendimento
projetado é saldo final menos total aportado. O arredondamento ocorre somente
na apresentação monetária.

Os campos aceitam aporte de R$ 0 a R$ 1 bilhão, taxa efetiva anual acima de
-100% até 1.000% e prazo inteiro entre 1 e 600 meses. Esses limites evitam
valores inválidos e crescimento numérico sem limite na interface; não são
recomendação de investimento.

## Estado e próximo passo

A entrega cobre apenas a frente A da #359. Quatro testes determinísticos da
fórmula passaram em 17/10/2026, assim como `npm run typecheck` e o build de
produção do frontend; o destino de validação vigente é `sig-v2` via Cloudflare
Tunnel (ver `docs/USER_VALIDATION_RUNBOOK.md`). O cálculo e a rota foram
validados por HTTP. A validação visual desktop/mobile continua pendente porque
não havia navegador integrado disponível nesta sessão. A calculadora de Renda
Fixa permanece separada: comparação tributável/isenta depende de regras e
premissas tributárias explicitamente validadas.
