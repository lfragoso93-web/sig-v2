# Dados canônicos e KPIs

> Última atualização: 14/07/2026

Este documento define a camada canônica usada para alimentar Resumo, Patrimônio, Rentabilidade e Dashboard.

---

## Objetivo

Evitar que cada página calcule seus próprios totais com regras diferentes.

```text
Transações + preços + proventos + benchmarks
        ↓
Serviços canônicos
        ↓
Contratos compartilhados
        ↓
Telas
```

---

## Fontes canônicas

| Fonte | Uso |
|---|---|
| `transactions` | Compras, vendas, taxas, moeda e câmbio informado |
| `assets` | Tipo, ticker, símbolo de provedor e metadados |
| `asset_prices` | Histórico de preços por ativo |
| `dividends` | Proventos materializados por carteira |
| `portfolio_snapshots` | Evolução patrimonial e TWR |
| benchmarks | CDI, Selic, IPCA, IGP-M, câmbio e demais índices |

---

## Resultado financeiro

Resultado financeiro deve considerar:

```text
ganho não realizado
+ ganho realizado
+ proventos recebidos
```

Esse valor é financeiro, em moeda, e não deve ser confundido com rentabilidade percentual.

---

## Rentabilidade

Rentabilidade percentual deve vir da cadeia TWR sempre que o objetivo for medir performance da carteira no tempo.

Períodos principais:

- hoje;
- mês;
- 12 meses;
- desde o início.

O retorno acumulado desde o início deve usar `accumulated_return_pct` do snapshot mais recente.

---

## Proventos

Proventos devem ser materializados por carteira antes dos snapshots.

A materialização considera:

- posição elegível na data correta;
- quantidade detida;
- valor por unidade;
- data de pagamento;
- tipo do provento;
- status recebido.

Eventos não monetários não entram no total financeiro recebido.

---

## KPIs principais

| KPI | Semântica |
|---|---|
| Patrimônio atual | Valor de mercado atual da carteira |
| Investido | Capital líquido aportado, conforme regra canônica |
| Resultado | Ganhos realizados + não realizados + proventos recebidos |
| Proventos | Total recebido ou período filtrado |
| Retorno hoje | TWR do último snapshot |
| Retorno mês | Composição diária do mês |
| Retorno 12m | Composição diária dos últimos 365 dias |
| Retorno desde início | Retorno acumulado persistido |

---

## Qualidade dos dados

Campos que devem chegar à UI:

- `has_partial_prices`
- `return_is_estimated`

A UI deve evitar apresentar esses avisos como erro fatal. Eles indicam que o valor foi calculado, mas depende de cobertura parcial ou inferência.

---

## Contrato legado

Campos legados podem continuar expostos durante a migração, mas devem apontar para os conceitos novos quando possível.

Exemplo:

```text
retorno_total_pct → TWR desde o início
```

---

## Pendências conhecidas

- Ajustar visualmente os cards da página Rentabilidade.
- Revalidar todos os cards da página Resumo com os contratos canônicos.
- Expor avisos visuais de cobertura parcial e retorno estimado.
- Finalizar consumo dedicado de Tesouro nos snapshots.
