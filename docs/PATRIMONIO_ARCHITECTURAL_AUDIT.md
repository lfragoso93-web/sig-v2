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
| `GET /performance/{id}/classes/reconciliation/latest` | consolidado x soma das classes na mesma data | consumido por Patrimônio |
| `GET /portfolios/{id}/reconciliation/intraday` | `summary.v2` x posições x distribuição | consumido por Patrimônio |
| `GET /performance/{id}/classes/{tipo}/evolution/daily` | snapshot por classe | hook existente, sem consumidor de página |
| `GET /performance/{id}/classes/{tipo}/evolution/monthly` | snapshot por classe | consumido apenas por Resumo |

Todos validam a propriedade da carteira e os seis endpoints de leitura agora
aplicam `response_model` Pydantic estrito, com rejeição de campos extras.

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
- concentração e top posições;
- integridade do valuation intradiário entre `summary.v2`, posições e distribuição;
- reconciliação do snapshot consolidado com snapshots por classe na mesma data.

Oferece seleção histórica consolidada ou por classe e consulta disponibilidade.
Estados sem data/base comparável permanecem neutros e não são convertidos em divergência.

### Hooks

`useEvolution.ts` concentra as séries consolidadas, por classe e disponibilidade.
`useReconciliation.ts` valida estritamente os contratos de reconciliação de
fechamento e intradiária antes de expô-los à página. Nenhum hook usa
`placeholderData` para ocultar a primeira carga.

## Inconsistências encontradas

1. ~~Contratos de resposta dos endpoints de performance não são estritos.~~ Resolvido com schemas versionados por fonte.
2. ~~A página Patrimônio não consome a fundação por classe já disponível.~~ Resolvido com seleção diária/mensal por classe.
3. ~~A reconciliação canônica existe no backend, mas não é observável na página.~~ Resolvido com painel de integridade separado por base temporal.
4. ~~O recorte mensal usa `months * 31`.~~ Resolvido com janela de meses-calendário compartilhada.
5. Loading, erro, vazio, aguardando backfill e classe sem motor possuem apresentação explícita na evolução.
6. ~~`frontend/src/services/portfolioService.ts` não possui consumidores e aponta para endpoint inexistente.~~ Resolvido pela remoção do cliente legado.
7. ~~O catálogo de opções de classe está duplicado no frontend.~~ Resolvido com seletor compartilhado alimentado pela disponibilidade do backend.
8. ~~`return_is_estimated` deve ser apresentado como qualidade, sem interpretação local.~~ Resolvido nos tooltips canônicos.

## Sequência segura

1. ~~Caracterizar contratos, períodos, disponibilidade e reconciliação.~~ Concluído.
2. ~~Remover o cliente legado comprovadamente sem consumidores.~~ Concluído.
3. ~~Introduzir schemas Pydantic estritos sem alterar valores.~~ Concluído.
4. ~~Tornar períodos e estados de consulta determinísticos.~~ Concluído.
5. ~~Criar apresentação reutilizável para evolução consolidada ou por classe.~~ Concluído.
6. ~~Integrar seleção, disponibilidade e qualidade em Patrimônio.~~ Concluído.
7. ~~Validar a soma das classes somente quando o backend declarar comparabilidade.~~ Concluído.
8. Sincronizar documentação e promover a Fase 3 por PR.

## Fora do escopo

- TWR de Tesouro Direto e Renda Fixa: Fase 4 / Issue #149.
- Histórico persistido do IBOV: Issue #150.
- Remoção integral do serviço legado de rentabilidade: Issue #151.
- Dependências #146, #138, #137 e #133: Issue #159.
- Rebuild destrutivo ou completo da base: Issue #158.

## Evidências do bloco inicial

- Cliente `portfolioService.ts` removido; nenhuma referência ou consumidor foi encontrado.
- Rota frontend obsoleta `/patrimonio-history` eliminada com o cliente.
- Testes caracterizam isolamento por carteira e fonte `portfolio_class_snapshot`.
- O mensal usa o último fechamento do período e compõe os TWRs diários.
- Disponibilidade exige simultaneamente motor suportado e snapshot materializado.
- Contratos estritos cobrem evolução consolidada e por classe, disponibilidade e reconciliação.
- Fontes históricas, estados e campos de reconciliação são validados sem recomputar valores.
- Janelas de 6, 12 e 24 meses começam no primeiro dia exato do mês inicial; `0` preserva todo o histórico.
- Consolidado e classes usam a mesma função de fronteira mensal.
- Loading, erro com retry, vazio real e sucesso são estados distintos na evolução.
- Suíte backend disponível: 89 testes aprovados.
- O router de performance possui teste de compilação do fonte após a correção do incidente de startup causado por escapes literais.
- Seleção por classe usa exclusivamente os tipos informados pelo endpoint de disponibilidade.
- Gráficos diário e mensal leem diretamente `market_value` e `cost_basis` dos contratos canônicos.
- Classes sem motor ou sem backfill exibem o motivo do backend e não disparam consulta de série.
- Tooltips diário e mensal exibem patrimônio, custo, resultados realizado e não realizado, TWR do período e acumulado.
- Fonte do snapshot, cobertura parcial e retorno estimado são apresentados diretamente pelos flags persistidos.
- Suíte frontend disponível: 68 testes aprovados e typecheck focado de Patrimônio válido.
- Testes de regressão impedem a comparação monetária entre valuation intradiário e snapshot fechado.
- O painel apresenta somente diferenças e estados calculados pelo backend; não há reconciliação financeira local.
- Nenhum workflow remoto foi disparado neste bloco.

## Próximo bloco recomendado

Executar as suítes finais da Fase 3, revisar consumidores legados remanescentes,
sincronizar README, ROADMAP e CHANGELOG e abrir a PR estrutural para `main`.
