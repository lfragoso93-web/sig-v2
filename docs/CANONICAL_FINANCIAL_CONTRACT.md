# Contrato Financeiro Canônico

Este documento define a semântica oficial dos indicadores financeiros do SGI V2.
Novos módulos não devem criar fórmulas paralelas para estes conceitos.

## Princípios

1. Valuation intradiário e performance fechada são domínios temporais diferentes.
2. Rentabilidade oficial é TWR; retorno simples não pode ser apresentado como TWR.
3. Proventos são reconhecidos quando efetivamente recebidos, pelo valor líquido.
4. Ausência de preço deve ser explícita e nunca transformar silenciosamente uma posição em zero.
5. Divergências são diagnosticadas; valores não são corrigidos silenciosamente.

## Indicadores

| Indicador | Definição canônica | Fonte |
|---|---|---|
| Patrimônio | Valor de mercado atual das posições abertas | Valuation intradiário |
| Total investido | Custo contábil atual das posições abertas | Posições e valuation canônico |
| Resultado não realizado | Patrimônio menos total investido | Derivado |
| Resultado realizado | Ganhos e perdas reconhecidos em vendas encerradas | Serviço de P&L realizado / snapshot |
| Resultado total | Não realizado + realizado + proventos recebidos | Derivado |
| Variação patrimonial % | Resultado não realizado dividido pelo custo atual | Derivado |
| Rentabilidade acumulada | TWR acumulado até o último fechamento disponível | Snapshot diário |
| Rentabilidade diária | TWR do último fechamento disponível | Snapshot diário |
| Proventos 12m | Eventos monetários líquidos recebidos nos últimos 365 dias | Agregação canônica de proventos |
| Proventos totais | Todos os eventos monetários líquidos recebidos | Agregação canônica de proventos |
| Cobertura de preços | Ativos precificáveis com preço dividido pelo total de ativos precificáveis | Valuation intradiário |

## Referências temporais

- `valuation_updated_at`: momento de referência dos preços usados no patrimônio intradiário.
- `performance_as_of`: data do snapshot fechado usado no TWR.
- `proventos_as_of`: data-limite dos proventos recebidos incluídos.
- `snapshot_date`: data do snapshot utilizado para performance e reconciliação.

É esperado que `valuation_updated_at` seja mais recente que `performance_as_of` durante o pregão.
Essa diferença não representa erro de reconciliação.

## Qualidade e estimativas

- `has_partial_prices=true`: existe ao menos um ativo precificável sem preço disponível.
- `assets_without_price`: lista dos tickers sem preço.
- `price_coverage_pct`: cobertura por quantidade de ativos precificáveis, não por peso patrimonial.
- `return_is_estimated=true`: o snapshot possui pelo menos uma premissa estimada.
- `summary_source=valuation_fallback`: não existe snapshot fechado; a rentabilidade não deve ser tratada como TWR oficial.

## Versão do Resumo

O endpoint da página Resumo usa o contrato `summary.v2`.

Características:

- campos extras são rejeitados;
- campos obrigatórios ausentes são rejeitados;
- aliases legados em inglês não são emitidos;
- entradas antigas de cache são descartadas e recalculadas;
- patrimônio intradiário e TWR fechado permanecem separados.

## Campos legados removidos

Os seguintes aliases não fazem parte de `summary.v2`:

```text
total_invested
current_value
total_gain
total_gain_pct
proventos_em_carteira
ganho_capital
```

Consumidores devem usar exclusivamente os nomes canônicos definidos no schema
`backend/app/schemas/portfolio_summary.py`.
