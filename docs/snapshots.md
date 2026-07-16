# Snapshots e rentabilidade TWR

> Última atualização: 14/07/2026

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
asset_prices + transactions + dividends
        ↓
portfolio_snapshot_twr_service
        ↓
portfolio_snapshots
```

Se faltar preço, o snapshot usa fallback patrimonial e marca `has_partial_prices=true`.

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
| Ativos cotados | Consulta `asset_prices` |
| Renda Fixa | Deve usar motor interno da classe |
| Tesouro Direto | Deve usar histórico dedicado da classe |
| Cripto | Usa histórico persistido, com roteamento em revisão |

Pendência conhecida: garantir que Tesouro Direto seja sempre avaliado no snapshot pela fonte dedicada, não por fallback genérico de preço médio.

---

## Reconstrução

A reconstrução completa ocorre por:

```bash
python -m app.cli.full_market_rebuild
```

Ou por manutenção específica do scheduler.

Após mudanças em proventos, preços ou transações retroativas, os snapshots devem ser reconstruídos a partir da primeira data afetada.
