# Rentabilidade

> Última atualização: 14/07/2026

Este documento define a semântica dos indicadores de rentabilidade do SGI v2.

---

## Separação fundamental

O sistema separa dois conceitos:

| Conceito | Tipo | Exemplo |
|---|---|---|
| Resultado financeiro | Valor monetário | R$ 1.250,00 |
| Rentabilidade | Percentual | 8,42% |

Resultado financeiro pode incluir ganho realizado, ganho não realizado e proventos. Rentabilidade deve ser calculada pela cadeia TWR quando o objetivo é medir performance no tempo.

---

## Cards recomendados

A página Rentabilidade deve apresentar quatro cards principais:

1. **Hoje**
2. **Mês**
3. **12 meses**
4. **Desde o início**

---

## Hoje

Fonte:

```text
daily_return_pct do último snapshot disponível
```

Representa a rentabilidade diária da carteira, ajustada por fluxos externos e proventos do dia.

---

## Mês

Fonte:

```text
composição dos retornos diários desde o início do mês
```

Não deve ser calculado apenas por diferença entre patrimônio atual e patrimônio do início do mês, pois aportes e retiradas distorcem a leitura.

---

## 12 meses

Fonte:

```text
composição dos retornos diários dos últimos 365 dias
```

Quando a carteira possui menos de 12 meses, usar o intervalo disponível e deixar claro na interface se necessário.

---

## Desde o início

Fonte:

```text
accumulated_return_pct do snapshot mais recente
```

Representa o retorno acumulado da carteira desde a primeira data processada.

---

## Composição

A composição de retornos segue:

```text
(1 + r1) × (1 + r2) × ... × (1 + rn) − 1
```

Exemplo:

```text
Dia 1: +2,00%
Dia 2: -1,00%
Resultado composto: +0,98%
```

---

## Resultado e proventos

O card Resultado, quando exibido na página Resumo ou Rentabilidade, deve representar:

```text
ganho realizado
+ ganho não realizado
+ proventos recebidos
```

Esse valor não é TWR e não deve ser comparado diretamente com os percentuais de rentabilidade.

---

## Flags de qualidade

A interface deve considerar:

| Flag | Exibição recomendada |
|---|---|
| `has_partial_prices` | Aviso de preço parcial ou estimado |
| `return_is_estimated` | Aviso de retorno estimado por fluxo inferido |

---

## Pendências visuais

- Reorganizar os cards da página Rentabilidade para a sequência oficial.
- Exibir badges/tooltip de qualidade quando houver preço parcial.
- Revalidar os cards da página Resumo contra a mesma camada canônica.
