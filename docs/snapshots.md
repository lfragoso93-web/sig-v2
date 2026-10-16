# Snapshots e rentabilidade TWR

> Última atualização: 16/10/2026

Este documento descreve como o SGI v2 reconstrói snapshots patrimoniais e calcula rentabilidade ponderada pelo tempo.

---

## Papel do snapshot

O snapshot diário consolida o estado da carteira em uma data:

- valor de mercado;
- custo em aberto;
- valor investido líquido;
- ganho realizado;
- ganho não realizado;
- resultado financeiro;
- fluxos externos do dia;
- proventos do dia;
- proventos acumulados;
- retorno diário;
- retorno acumulado.

---

## Regra DB-only

O motor de snapshots não chama provedores externos.

```text
transactions + asset_prices + rate_history + fx_rates + asset_dividends
        ↓
calculate_canonical_portfolio_totals()
        ↓
backfill_canonical_snapshots_with_returns()
        ↓
portfolio_snapshots
```

O writer usa somente dados persistidos e não chama provedores. Lacuna de preço
persistido de ativo de mercado faz a data ser ignorada; cobertura incompleta de
benchmark interrompe a reconstrução naquela data. Nenhum desses casos deve ser
preenchido com cotação inventada.

---

## Fluxos externos

Como o sistema ainda não possui conta-caixa explícita, fluxos externos são inferidos a partir das transações:

- compra: aporte;
- venda: retirada;
- taxas: ajustam o fluxo conforme a operação.

Por isso, `return_is_estimated` pode permanecer verdadeiro em cenários onde a rentabilidade depende de inferência de caixa.

---

## Proventos

Proventos monetários entram no TWR pelo dia de pagamento.

São considerados:

- dividendos;
- JCP;
- rendimentos;
- amortizações monetárias.

Eventos não monetários, como bonificação e subscrição, não entram como rendimento financeiro direto.

---

## Fórmula do retorno diário

Conceitualmente:

```text
retorno_dia = (valor_final - valor_inicial - fluxo_liquido + proventos_dia) / valor_inicial
```

O serviço aplica as proteções necessárias para início de carteira, dias sem posição e ausência de base.

---

## Retorno acumulado

O retorno acumulado é composto diariamente:

```text
(1 + r1) × (1 + r2) × ... × (1 + rn) − 1
```

Esse acumulado é gravado no snapshot mais recente como `accumulated_return_pct`.

---

## Fechamento mensal

O fechamento mensal usa o último snapshot disponível de cada mês. O retorno mensal deve ser calculado pela composição dos retornos diários do período, não por variação simples de PnL.

Exemplo:

```text
Dia 1: +2,00%
Dia 2: -1,00%
Mensal: +0,98%
```

---

## Campos de qualidade

| Campo | Significado |
|---|---|
| `has_partial_prices` | Algum ativo aberto não tinha preço persistido para a data/janela |
| `return_is_estimated` | O retorno depende de inferências, principalmente fluxo externo sem conta-caixa |

A interface deve exibir essas flags de forma clara quando disponíveis.

---

## Classes especiais

| Classe | Tratamento no snapshot |
|---|---|
| Ativos cotados | Usa `asset_prices` persistido com resolução lifecycle-aware |
| Renda Fixa | Usa accrual dedicado derivado de `transactions` e cobertura persistida de indexadores |
| Tesouro Direto | Aplica correção dedicada por símbolo canônico e PU persistido em `asset_prices` |
| Cripto | Usa histórico persistido, com roteamento em revisão |

### Lacuna de qualidade do Tesouro

O valuation agregado começa com a base por custo e a substitui pela correção
dedicada quando símbolo e PU persistido são resolvidos. Se essa resolução falha,
o valor-base por custo permanece. Embora o valuation produza o diagnóstico
`treasury_unresolved`, o writer não o persiste e a checagem atual de
`has_partial_prices` exclui Tesouro Direto. Portanto, o snapshot agregado pode
não marcar essa cobertura como parcial.

Esse caminho não deve ser tratado como valuation completo nem como TWR oficial
até que a qualidade do snapshot propague a ausência de PU. O tratamento pertence
a uma correção técnica separada; não inferir preço ou identidade do título.

---

## Reconstrução

A writer canônico de snapshots é:

```text
backfill_canonical_snapshots_with_returns()
```

A reconstrução operacional pode ser iniciada por:

```bash
python -m app.cli.full_market_rebuild
```

Ou pela manutenção específica do scheduler, que chama o mesmo writer.

Após mudanças em proventos, preços ou transações retroativas, os snapshots devem ser reconstruídos a partir da primeira data afetada.
