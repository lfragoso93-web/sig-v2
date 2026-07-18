# Auditoria arquitetural da página Resumo

Issue de acompanhamento: #161  
Branch: `stable-15jun`  
Referência: 17/07/2026

## Objetivo

Este documento inventaria os contratos, endpoints e consumidores atuais da página
Resumo durante as correções funcionais. A página deve permanecer uma projeção do
domínio financeiro canônico; nenhum consumidor frontend pode criar uma fórmula
financeira concorrente.

## Princípios de reconciliação

- Valuation intradiário e TWR de fechamento são referências temporais distintas.
- Valores monetários equivalentes devem reconciliar com tolerância de R$ 0,01.
- Percentuais equivalentes devem reconciliar com tolerância de 0,0001 ponto percentual.
- Ausência de preço, ausência de snapshot e estimativas devem permanecer explícitas.
- Resultado atual não pode reutilizar silenciosamente um componente monetário defasado.
- Histórico consolidado e histórico por classe devem vir de snapshots persistidos.

## Inventário de consumidores

| Área do Resumo | Hook frontend | Endpoint | Serviço backend | Fonte atual |
|---|---|---|---|---|
| KPIs | `usePortfolioSummaryData` | `GET /portfolios/{id}/summary` | `portfolio_summary_service` | Valuation intradiário + último `PortfolioSnapshot` + proventos recebidos |
| Tabela de ativos | `usePositions` | `GET /portfolios/{id}/positions` | `canonical_positions_service` | Posições/valuation atual + proventos recebidos por ticker |
| Gráfico consolidado | `usePatrimonioHistory` | `GET /portfolios/{id}/patrimonio-history` | `portfolio_history_service` | Último `PortfolioSnapshot` de cada mês |
| Gráfico por classe | `usePatrimonioHistory` | `GET /portfolios/{id}/patrimonio-history?asset_type=...` | `portfolio_class_evolution_service` | Recomposição por transações e preços históricos |
| Gráfico canônico consolidado já disponível | `useMonthlyEvolution` | `GET /performance/{id}/evolution/monthly` | leitura de snapshots enriquecidos | `PortfolioSnapshot` |
| Gráfico canônico por classe já disponível | `useClassMonthlyEvolution` | `GET /performance/{id}/classes/{type}/evolution/monthly` | leitura de snapshots por classe | `PortfolioClassSnapshot` |
| Disponibilidade por classe | `useClassTwrAvailability` | `GET /performance/{id}/classes/availability` | leitura de snapshots por classe | Cobertura e suporte do motor histórico |
| Reconciliação por classe | `useClassReconciliation` | `GET /performance/{id}/classes/reconciliation/latest` | reconciliação de classes | Snapshots consolidados e por classe |
| Reconciliação intradiária | auditoria operacional | `GET /portfolios/{id}/reconciliation/intraday` | `portfolio_intraday_reconciliation_service` | `summary.v2` + posições + distribuição, sem snapshots |

## Matriz dos KPIs

| KPI/campo | Fórmula canônica | Referência | Fonte atual | Consumidores |
|---|---|---|---|---|
| `total_patrimonio` | Soma do valor atual das posições abertas | Intradiária | Valuation canônico | Resumo e Patrimônio |
| `total_investido` | Custo contábil atual das posições abertas | Intradiária | Valuation canônico | Resumo e Patrimônio |
| `ganho_nao_realizado` / `variacao_valor` | Patrimônio menos custo atual | Intradiária | Derivado no backend | Resumo, Patrimônio e tabela |
| `ganho_realizado` | Ganhos/perdas reconhecidos em vendas | Atual | Serviço canônico de P&L realizado | Resumo e Patrimônio |
| `total_proventos` | Eventos monetários líquidos recebidos | Data de pagamento até hoje | Agregação canônica | Resumo e Patrimônio |
| `lucro_total` | Não realizado + realizado + proventos | Atual | Valuation + P&L realizado + proventos atuais | Resumo e Patrimônio |
| `rentabilidade_total` | TWR acumulada; fallback identificado como estimativa quando não há snapshot | Fechamento ou estimativa intradiária explícita | Snapshot ou `valuation_fallback` | Resumo e Patrimônio |
| `rentabilidade_diaria` | TWR diária | Último fechamento | Último snapshot | Resumo |
| `dividendos_recebidos_12m` | Eventos líquidos dos últimos 365 dias | Até hoje | Agregação canônica | Resumo |
| `price_coverage_pct` | Ativos precificáveis cobertos / total | Intradiária | Valuation canônico | Metadados de qualidade |

## Achados arquiteturais

### A1 — Resolvido: resultado realizado atual separado do TWR fechado

`portfolio_summary_service` usa o serviço canônico de P&L realizado para
`ganho_realizado` e `lucro_total`. O último snapshot permanece exclusivamente como
fonte do TWR acumulado, TWR diário e metadados de performance fechada.

### A2 — Gráfico por classe ainda contorna `PortfolioClassSnapshot`

O filtro por classe do Resumo chama
`portfolio_class_evolution_service.get_monthly_evolution_by_class`, que recompõe
quantidade, custo e valor por transações e preços históricos e usa custo médio
quando falta cotação. Isso produz `history_source=db_derived_class_history` e cria
uma segunda regra financeira fora do pipeline de snapshots.

Direção: migrar o Resumo para os endpoints de `PortfolioClassSnapshot`, respeitar
a disponibilidade por classe e não exibir aproximação para motores ainda não
suportados.

### A3 — Endpoint histórico redundante

`/portfolios/{id}/patrimonio-history` replica parte do domínio já publicado em
`/performance/{id}/evolution/monthly` e alterna entre duas fontes conforme o
filtro. Isso torna o contrato temporal dependente de um parâmetro.

Direção: migrar o consumidor do Resumo para os endpoints `/performance`; depois
de confirmar ausência de outros consumidores, descontinuar o endpoint redundante
em bloco separado.

### A4 — Resolvido: campo legado de rentabilidade removido

`PositionGroup.rentabilidade_pct` e o ramo visual “Rentab. total” foram removidos.
O contrato backend de posições rejeita campos de retorno legado. Rentabilidade por
classe só poderá retornar por `PortfolioClassSnapshot`, com referência e
disponibilidade explícitas.

### A5 — Mapeamento permissivo pode mascarar quebra de contrato

`PortfolioSummaryLike` torna campos obrigatórios opcionais e `safeNum` converte
ausência ou valor inválido em zero. Embora o backend valide `summary.v2` com
`extra="forbid"`, o frontend pode transformar payload incompleto em KPI zero.

Direção: consumir o tipo estrito `PortfolioSummary` e rejeitar/explicitar payload
inválido. Zero financeiro válido deve continuar distinto de ausência de dado.

### A6 — Resolvido: consumidores intradiários reconciliados entre si

`GET /portfolios/{id}/reconciliation/intraday` materializa `summary.v2`, grupos
de posições e distribuição por classe na mesma requisição. O serviço compara
patrimônio, custo, resultado não realizado e resultado de capital por grupo com
tolerância de R$ 0,01.

O contrato declara `valuation_mode=intraday` e `snapshot_evaluated=false`.
TWR, rentabilidade e valores de fechamento não participam dessas comparações.

### A7 — Resolvido: dropdown em portal coberto por regressão

O menu de ativos usa `createPortal`, coordenadas de viewport e reposição em
scroll/resize. A cobertura frontend valida o comportamento com uma e vinte linhas.

### A8 — Correção do gráfico aguarda validação visual

`PatrimonioBarChart` já usa `stackOffset="sign"` e possui teste de transformação
para ganho/perda. A issue #147 permanece aberta até validação no ambiente
publicado.

### A9 — Resolvido: contrato e totais por classe

`GET /portfolios/{id}/positions` possui `response_model` estrito para grupos e
posições. `total_invested` é obrigatório e o frontend consome esse total canônico
diretamente, sem somar valores arredondados por posição. A6 cobre a reconciliação
automatizada com os demais consumidores intradiários.

### A10 — Resolvido: estados e semântica da tabela

A primeira consulta de posições preserva o estado de carregamento até a resposta
real, sem usar lista vazia como placeholder. A interface distingue custo atual,
valor atual, resultado de capital e variação diária. Ativos sem preço exibem
“Sem cotação”, enquanto o aviso consolidado lista a cobertura parcial.

Quando `summary.v2` retorna `valuation_fallback`/`return_is_estimated`, o card
usa “Retorno estimado” e informa que o TWR está indisponível sem snapshot. O
fallback não é apresentado como rentabilidade TWR.

## Contratos que devem permanecer

- `summary.v2` como contrato único dos KPIs.
- `GET /portfolios/{id}/positions` como contrato canônico da tabela, após limpeza
  dos campos legados.
- `PortfolioSnapshot` para histórico consolidado e TWR.
- `PortfolioClassSnapshot` para histórico e TWR por classe.
- Agregação canônica de eventos monetários recebidos para proventos.
- Valuation canônico por classe para patrimônio e custo atuais.

## Sequência recomendada de correção

1. Concluído: demonstrar por teste o P&L realizado defasado.
2. Concluído: corrigir a composição monetária atual do `summary.v2` sem alterar TWR.
3. Concluído: remover o retorno legado, validar o contrato de posições e cobrir o dropdown.
4. Concluído: reconciliar `summary.v2`, posições e distribuição na referência intradiária.
5. Concluído: explicitar loading, vazio, cobertura parcial, preço ausente e retorno estimado.
6. Migrar o gráfico consolidado e por classe para os endpoints de performance.
7. Remover o endpoint/recomposição redundante somente após auditar consumidores.
8. Validar visualmente a #147.
9. Sincronizar documentação viva ao concluir o bloco estrutural.
