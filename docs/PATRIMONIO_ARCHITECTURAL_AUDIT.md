# Auditoria arquitetural — Patrimônio

> Issue de controle: [#148](https://github.com/lfragoso93-web/sig-v2/issues/148)
>
> Estado auditado: 19/07/2026, início da Fase 3 após a PR #166.

## Objetivo

Restaurar a evolução histórica por classe na página Patrimônio usando somente
snapshots persistidos, sem misturar valuation intradiário com performance
fechada e sem criar cálculos financeiros paralelos no frontend.

## Fronteiras financeiras

| Contexto | Fonte canônica | Uso |
|---|---|---|
| Patrimônio atual | valuation intradiário e posições canônicas | KPIs, distribuição e concentração atuais |
| Histórico consolidado | `PortfolioSnapshot` | evolução diária e mensal da carteira |
| Histórico por classe | `PortfolioClassSnapshot` | evolução diária e mensal da classe |
| Rentabilidade histórica | TWR persistido no snapshot | tooltip e análise; nunca retorno simples |
| Qualidade | cobertura, estimativa e status do valuation | avisos e indisponibilidade |

Os números atuais e históricos possuem datas de referência diferentes por
contrato. A interface deve apresentá-las, não tentar reconciliá-las como se
fossem o mesmo fechamento.

## Fundação existente

### Persistência por classe

`PortfolioClassSnapshot` possui chave única por carteira, classe e data e
armazena:

- `market_value` e `cost_basis`;
- `realized_pnl` e `unrealized_pnl`;
- `net_external_flow`;
- `dividends_day` e `dividends_accumulated`;
- `daily_return_pct` e `accumulated_return_pct`;
- `has_partial_prices`, `return_is_estimated` e `valuation_status`.

A reconstrução é DB-first e refaz a cadeia completa para não reiniciar TWR no
meio da série.

### Classes

O motor atual suporta ações, FIIs, ETFs nacionais e internacionais, stocks,
BDRs e cripto. Tesouro Direto e Renda Fixa exigem motor histórico dedicado e
permanecem explicitamente indisponíveis até a Fase 4.

## Endpoints existentes

| Endpoint | Fonte | Situação |
|---|---|---|
| `GET /performance/{id}/evolution/daily` | snapshot consolidado | consumido por Patrimônio |
| `GET /performance/{id}/evolution/monthly` | snapshot consolidado | consumido por Patrimônio e Resumo |
| `GET /performance/{id}/classes/availability` | carteira + snapshots por classe | consumido apenas por Resumo |
| `GET /performance/{id}/classes/reconciliation/latest` | consolidado x soma das classes | sem consumidor frontend |
| `GET /performance/{id}/classes/{tipo}/evolution/daily` | snapshot por classe | hook existente, sem consumidor de página |
| `GET /performance/{id}/classes/{tipo}/evolution/monthly` | snapshot por classe | consumido apenas por Resumo |

Todos validam a propriedade da carteira, mas ainda retornam dicionários sem
`response_model` Pydantic estrito.

## Consumidores frontend

### Página Resumo

Já seleciona classes, consulta disponibilidade e usa a evolução mensal por
classe. Esse fluxo é referência funcional, mas contém catálogo local de rótulos
que deve ser comparado ao catálogo canônico antes de qualquer reutilização.

### Página Patrimônio

Exibe:

- KPIs atuais vindos de `summary.v2`;
- evolução consolidada diária e mensal;
- distribuição intradiária por classe;
- concentração e top posições.

Não oferece seleção histórica por classe e não consulta disponibilidade nem
reconciliação.

### Hooks

`useEvolution.ts` já contém hooks consolidados, por classe, disponibilidade e
reconciliação. Os hooks diários usam `placeholderData: []`, o que pode ocultar o
primeiro estado de loading; os mensais preservam `undefined` durante a carga.

## Inconsistências encontradas

1. Contratos de resposta dos endpoints de performance não são estritos.
2. A página Patrimônio não consome a fundação por classe já disponível.
3. A reconciliação canônica existe no backend, mas não é observável na página.
4. O recorte mensal usa `months * 31`, aproximação que não representa uma
   fronteira mensal determinística.
5. Loading, erro, vazio, aguardando backfill e classe sem motor ainda não têm
   estados uniformes.
6. `frontend/src/services/portfolioService.ts` não possui consumidores e aponta
   para `/patrimonio-history`, endpoint inexistente.
7. O catálogo de opções de classe está duplicado no frontend.
8. `return_is_estimated` é materializado como verdadeiro no motor atual e deve
   ser apresentado como qualidade, sem interpretação local.

## Sequência segura

1. Caracterizar contratos, períodos, disponibilidade e reconciliação.
2. Remover o cliente legado comprovadamente sem consumidores.
3. Introduzir schemas Pydantic estritos sem alterar valores.
4. Tornar períodos e estados de consulta determinísticos.
5. Criar apresentação reutilizável para evolução consolidada ou por classe.
6. Integrar seleção, disponibilidade, qualidade e reconciliação em Patrimônio.
7. Validar a soma das classes somente quando o backend declarar comparabilidade.
8. Sincronizar documentação e promover a Fase 3 por PR.

## Fora do escopo

- TWR de Tesouro Direto e Renda Fixa: Fase 4 / Issue #149.
- Histórico persistido do IBOV: Issue #150.
- Remoção integral do serviço legado de rentabilidade: Issue #151.
- Dependências #146, #138, #137 e #133: Issue #159.
- Rebuild destrutivo ou completo da base: Issue #158.

## Próximo bloco recomendado

Adicionar testes de caracterização dos payloads diário/mensal, disponibilidade,
reconciliação e isolamento por carteira antes de introduzir schemas estritos.
